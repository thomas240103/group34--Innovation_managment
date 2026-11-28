"""The common set of firms of the Magic Quadrant: one present score and one future score for the SAME firms.

Step 3 (Section 11) and Step 4 (Sections 6-7) import these functions, so that both axes of the quadrant are computed on
one list of firms and with one rule for missing values. Everything here is plain pandas, tested in
tests/test_quadrant.py. Nothing queries PATSTAT.

Why a second present score? The course present score (Step 3, Sections 5-9) needs five complete years of citations and
decided applications, so it can only measure firms whose families are old. On those indicators the firms that file
today (most of them since 2023) have no value at all, and the firms that stopped filing years ago keep the score of a
portfolio that has mostly lapsed. For the quadrant we measure the same four dimensions *as of today*:

- Volume: the firm's share of the sector's living families, each weighted by (1 - delta)^(age) (a depreciated patent
  stock, Hall, Jaffe & Trajtenberg 2005);
- Influence: citations received so far, divided by the mean of the families of the same priority year (and office of
  first filing, when the cohort is large enough), so a young family is compared with families of its own age;
- Success: share of national applications granted, on applications old enough to have been decided;
- Globalization: share of families with a PCT application or filed in 2+ offices, divided by the share of the families
  of the same priority year (an age-adjusted ratio).
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd

QUADRANT_INDICATORS = ["Volume", "Influence", "Success", "Globalization"]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def hierarchical_cohort_mean(
    df: pd.DataFrame,
    value_col: str,
    levels: Sequence[Sequence[str]],
    min_cohort: int = 20,
) -> pd.Series:
    """Mean of `value_col` in the finest cohort that has at least `min_cohort` rows.

    `levels` goes from the finest to the coarsest, e.g. [["priority_year", "first_office"], ["priority_year"]].
    The last level is always used when the finer ones are too small, whatever its size.
    """
    out = pd.Series(np.nan, index=df.index, dtype=float)
    for i, cols in enumerate(levels):
        cols = list(cols)
        grp = df.groupby(cols)[value_col]
        size = grp.transform("size")
        mean = grp.transform("mean")
        last = i == len(levels) - 1
        use = out.isna() & (size >= min_cohort if not last else True)
        out[use] = mean[use]
    return out


def depreciation_weight(priority_year: pd.Series, reference_year: int, delta: float = 0.15) -> pd.Series:
    """(1 - delta)^(reference_year - priority_year): the weight of a family in a depreciated stock (age >= 0)."""
    age = (reference_year - priority_year.astype(float)).clip(lower=0)
    return (1.0 - delta) ** age


def first_office(apps: pd.DataFrame) -> pd.Series:
    """Office of the first national filing of each family (ties: alphabetical); 'WO' only if nothing else exists."""
    a = apps[["docdb_family_id", "appln_auth", "appln_filing_date"]].copy()
    a["appln_auth"] = a["appln_auth"].astype(str).str.strip()
    a["is_wo"] = a["appln_auth"].eq("WO")
    a["date"] = pd.to_datetime(a["appln_filing_date"], errors="coerce")
    a = a.sort_values(["docdb_family_id", "is_wo", "date", "appln_auth"])
    return a.drop_duplicates("docdb_family_id").set_index("docdb_family_id")["appln_auth"]


# ---------------------------------------------------------------------------
# family-level inputs of the four "today" indicators
# ---------------------------------------------------------------------------
def family_today_table(
    families: pd.DataFrame,
    apps: pd.DataFrame,
    fwd_pairs: pd.DataFrame,
    alive: pd.Series,
    reference_year: int,
    delta: float = 0.15,
    influence_last_year: Optional[int] = None,
    globalization_last_year: Optional[int] = None,
    success_last_year: Optional[int] = None,
    min_cohort: int = 20,
) -> pd.DataFrame:
    """One row per family of the pool (sector + any extension) with the inputs of the four indicators.

    families: docdb_family_id, priority_year (one row per family: the POOL used as denominator and as cohort)
    apps: docdb_family_id, appln_id, appln_auth, appln_kind, appln_filing_year, appln_filing_date, granted
    fwd_pairs: docdb_family_id (cited), citing_family (any year; self-family pairs already removed)
    alive: boolean Series indexed by docdb_family_id (in force at the reference year)
    """
    fam = families[["docdb_family_id", "priority_year"]].drop_duplicates("docdb_family_id").copy()
    fam["priority_year"] = fam["priority_year"].astype(int)
    fam = fam.set_index("docdb_family_id")

    a = apps.copy()
    a["appln_auth"] = a["appln_auth"].astype(str).str.strip()
    kind = a["appln_kind"].astype(str).str.strip() if "appln_kind" in a.columns else pd.Series("", index=a.index)
    national = a[(a["appln_auth"] != "WO") & (kind != "T")].copy()
    granted = national["granted"].astype(str).str.strip().str.upper().isin(["Y", "1", "TRUE"])
    national["is_granted"] = granted

    fam["first_office"] = first_office(a).reindex(fam.index).fillna("OTHER")
    fam["first_office_group"] = np.where(fam["first_office"].eq("CN"), "CN", "other")
    fam["offices"] = national.groupby("docdb_family_id")["appln_auth"].nunique().reindex(fam.index).fillna(1)
    has_wo = a[a["appln_auth"].eq("WO")].groupby("docdb_family_id").size().gt(0)
    fam["has_pct"] = has_wo.reindex(fam.index, fill_value=False).astype(bool)
    fam["is_alive"] = alive.reindex(fam.index).fillna(False).astype(bool)

    # Volume: depreciated living stock
    fam["stock_weight"] = np.where(fam["is_alive"], depreciation_weight(fam["priority_year"], reference_year, delta), 0.0)

    # Influence: citations to date, relative to families of the same age (and office of first filing if possible)
    cites = fwd_pairs.groupby("docdb_family_id")["citing_family"].nunique() if len(fwd_pairs) else pd.Series(dtype=float)
    fam["cites_to_date"] = cites.reindex(fam.index).fillna(0.0)
    inf_last = influence_last_year if influence_last_year is not None else reference_year - 2
    old = fam["priority_year"] <= inf_last
    fam["influence_rel"] = np.nan
    if old.any():
        sub = fam.loc[old].reset_index()
        bench = hierarchical_cohort_mean(sub, "cites_to_date",
                                         [["priority_year", "first_office_group"], ["priority_year"]], min_cohort)
        rel = np.where(bench > 0, sub["cites_to_date"] / bench, np.nan)
        fam.loc[sub["docdb_family_id"].to_numpy(), "influence_rel"] = rel

    # Globalization: international intent (PCT or 2+ offices), relative to the families of the same priority year
    glob_last = globalization_last_year if globalization_last_year is not None else reference_year - 3
    fam["intl"] = (fam["has_pct"] | (fam["offices"] >= 2)).astype(float)
    fam["globalization_rel"] = np.nan
    okg = fam["priority_year"] <= glob_last
    if okg.any():
        sub = fam.loc[okg].reset_index()
        bench = hierarchical_cohort_mean(sub, "intl", [["priority_year"]], min_cohort)
        fam.loc[sub["docdb_family_id"].to_numpy(), "globalization_rel"] = np.where(bench > 0, sub["intl"] / bench, np.nan)

    # Success: share of the family's national applications granted, filed up to success_last_year
    suc_last = success_last_year if success_last_year is not None else reference_year - 6
    old_apps = national[pd.to_numeric(national["appln_filing_year"], errors="coerce") <= suc_last]
    fam["success_share"] = old_apps.groupby("docdb_family_id")["is_granted"].mean().reindex(fam.index)
    return fam


def firm_today_indicators(
    fam_table: pd.DataFrame,
    firm_families: pd.DataFrame,
    firms: Sequence[str],
    min_families: int = 5,
) -> pd.DataFrame:
    """The four 'today' indicators for each firm, with the number of families each rests on.

    firm_families: docdb_family_id, firm (a family of several firms counts fully for each, as in Step 3).
    An indicator resting on fewer than `min_families` families is left empty (NaN), Volume excepted.
    """
    ff = firm_families[["docdb_family_id", "firm"]].drop_duplicates()
    ff = ff[ff["firm"].isin(firms)].join(fam_table, on="docdb_family_id", how="inner")
    total_stock = max(float(fam_table["stock_weight"].sum()), 1e-12)
    g = ff.groupby("firm")
    out = pd.DataFrame(index=pd.Index(list(firms), name="firm"))
    out["families"] = g["docdb_family_id"].nunique()
    out["living families"] = g["is_alive"].sum()
    out["Volume"] = g["stock_weight"].sum() / total_stock * 100.0
    for name, col in (("Influence", "influence_rel"), ("Success", "success_share"), ("Globalization", "globalization_rel")):
        n = g[col].count()
        val = g[col].mean()
        if name == "Success":
            val = val * 100.0
        out[f"n {name}"] = n
        out[name] = val.where(n >= min_families)
    out["n Volume"] = out["families"]
    out = out.fillna({"families": 0, "living families": 0, "Volume": 0.0,
                      "n Influence": 0, "n Success": 0, "n Globalization": 0, "n Volume": 0})
    return out


# ---------------------------------------------------------------------------
# combining indicators (RRF, as Step 3 Section 7) with explicit missing values
# ---------------------------------------------------------------------------
def combine_rrf(
    table: pd.DataFrame,
    weights: Dict[str, float],
    min_indicators: int = 2,
    c: Optional[int] = None,
) -> pd.DataFrame:
    """Weighted Reciprocal Rank Fusion (Cormack et al. 2009): 100 = first on every indicator it has.

    The weights of a firm are rescaled over the indicators it has; a firm with fewer than `min_indicators`
    gets no score. Returns score, indicators used and the flag `provisional` (fewer than all indicators).
    """
    w = pd.Series(weights, dtype=float)
    t = table[w.index].astype(float)
    cc = len(t) if c is None else c
    parts = (cc + 1) / (cc + t.rank(ascending=False, method="min"))
    w_firm = t.notna().mul(w, axis=1)
    w_firm = w_firm.div(w_firm.sum(axis=1).replace(0, np.nan), axis=0)
    score = 100 * (parts * w_firm).sum(axis=1, min_count=1)
    used = t.notna().sum(axis=1)
    score = score.where(used >= min_indicators)
    return pd.DataFrame({"score": score, "indicators used": used, "provisional": used < len(w)})


# ---------------------------------------------------------------------------
# future score on the common set of firms
# ---------------------------------------------------------------------------
def shrink_mean(mean: pd.Series, n: pd.Series, prior: float, strength: float = 10.0) -> pd.Series:
    """Empirical-Bayes style shrinkage of a firm mean towards the sector prior: (n*mean + k*prior) / (n + k).

    A firm with 3 families moves little away from the prior; one with 90 keeps almost its own mean.
    """
    n = n.astype(float)
    return (n * mean + strength * prior) / (n + strength)


def common_future_scores(
    family_probs: pd.DataFrame,
    firms: Sequence[str],
    all_firm_families: pd.DataFrame,
    prior: float,
    strength: float = 10.0,
    weights: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """Future score of every firm of the common set, including firms with no recent family.

    family_probs: docdb_family_id, firm, prob (calibrated probability of each RECENT family)
    all_firm_families: docdb_family_id, firm (all years), to measure how much of the firm's work is recent
    Components (percentile ranks inside the common set, then weighted):
      quality  = shrunk mean probability of the recent families (Section 6 of Step 4)
      scale    = expected breakthroughs, the sum of the probabilities
      momentum = share of the firm's families that are recent
    A firm without recent families gets 0 on every component and the flag `no recent families`.
    """
    weights = weights or {"quality": 0.5, "scale": 0.3, "momentum": 0.2}
    fp = family_probs[family_probs["firm"].isin(firms)].dropna(subset=["prob"]).drop_duplicates(["docdb_family_id", "firm"])
    g = fp.groupby("firm")["prob"]
    out = pd.DataFrame(index=pd.Index(list(firms), name="firm"))
    out["recent families"] = g.size().reindex(out.index).fillna(0).astype(int)
    out["mean prob (raw)"] = g.mean().reindex(out.index)
    out["mean prob (shrunk)"] = shrink_mean(out["mean prob (raw)"], out["recent families"], prior, strength)
    out["expected breakthroughs"] = g.sum().reindex(out.index).fillna(0.0)
    out["top3 mean prob"] = g.apply(lambda s: float(np.mean(np.sort(s.to_numpy())[::-1][:3]))).reindex(out.index)
    allf = all_firm_families[all_firm_families["firm"].isin(firms)].drop_duplicates(["docdb_family_id", "firm"])
    total = allf.groupby("firm")["docdb_family_id"].nunique().reindex(out.index)
    out["all families"] = total.fillna(0).astype(int)
    out["momentum"] = (out["recent families"] / total).reindex(out.index).fillna(0.0)
    out["no recent families"] = out["recent families"].eq(0)

    comp = pd.DataFrame({
        "quality": out["mean prob (shrunk)"].where(~out["no recent families"]),
        "scale": out["expected breakthroughs"].where(~out["no recent families"]),
        "momentum": out["momentum"].where(~out["no recent families"]),
    })
    ranks = comp.rank(pct=True)                      # NaN for firms without recent families
    w = pd.Series(weights, dtype=float)
    out["future_score"] = (100 * (ranks[w.index] * w).sum(axis=1) / w.sum()).where(~out["no recent families"], 0.0)
    return out.sort_values("future_score", ascending=False)


def quadrant_label(present: float, future: float, present_cut: float, future_cut: float) -> str:
    """Gartner-style quadrant (kick-off): Leaders, Challengers, Visionaries, Niche players."""
    if pd.isna(present) or pd.isna(future):
        return "not placed"
    hi_p, hi_f = present >= present_cut, future >= future_cut
    if hi_p and hi_f:
        return "Leader"
    if hi_p:
        return "Challenger"
    if hi_f:
        return "Visionary"
    return "Niche player"
