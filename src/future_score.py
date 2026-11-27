"""Step 4 · Future Score engine: strictly causal ex-ante features, zero-leakage Arts et al. (2021)
lexical novelty, recombinant novelty (NR/NTO), dynamic t0+2y network metrics (PageRank, CD index,
generality), rolling out-of-time backtesting, bootstrap PR-AUC / Precision@K evaluation, rule-based
scorecard, and multi-aggregation firm scoring for Step 5 Magic Quadrant.

Designed to be imported by step4_future_score.ipynb and unit-tested locally.
"""
from __future__ import annotations

import itertools
import re
from collections import Counter
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


# ---------------------------------------------------------------------------
# 1. Target Labeling (Cohort Top-Decile Breakthroughs & Economic Expansion)
# ---------------------------------------------------------------------------
def label_top_decile_by_cohort(
    df: pd.DataFrame,
    value_col: str = "fwd_cites_5y",
    year_col: str = "priority_year",
    group_col: str = "main_subclass",
    top_share: float = 0.10,
    min_cohort: int = 30,
) -> Tuple[pd.Series, pd.Series]:
    """Flag families in the top `top_share` of their (year x subclass) cohort (falling back to year).

    Requires strictly positive `value_col > 0` so uncited patents never enter the top decile.
    """
    cohort = df[year_col].astype(str) + "|" + df[group_col].fillna("none").astype(str)
    counts = cohort.map(cohort.value_counts())
    cohort = cohort.where(counts >= min_cohort, df[year_col].astype(str))
    thresh = df.groupby(cohort)[value_col].transform(lambda s: s.quantile(1.0 - top_share))
    y = ((df[value_col] >= thresh) & (df[value_col] > 0)).astype(int)
    return y, cohort


# ---------------------------------------------------------------------------
# 2. Strictly Causal Ex-Ante Features (NR, NTO, Hot-Subfield Momentum, Arts Novelty)
# ---------------------------------------------------------------------------
def compute_originality_and_tct(
    bwd_df: pd.DataFrame,
    family_years: pd.Series,
) -> pd.DataFrame:
    """Compute Trajtenberg et al. (1997) Originality and Technology Cycle Time (median age of cited).

    `bwd_df` must have columns: `docdb_family_id`, `cited_family`, `cited_subclass`, `cited_year`.
    """
    if not len(bwd_df):
        return pd.DataFrame(columns=["originality", "tech_cycle_time", "n_bwd_cited_fams"])

    df = bwd_df.copy()
    df["priority_year"] = df["docdb_family_id"].map(family_years)
    # Only strictly prior cited families (avoid dirty future dates)
    valid_age = df["priority_year"] - df["cited_year"]
    df["cite_age"] = valid_age.where(valid_age >= 0)

    # Originality: 1 - sum(s_j^2) over cited 4-char subclasses (with Hall bias correction optional; standard HHI)
    sub = df.dropna(subset=["cited_subclass"]).copy()
    sub = sub[sub["cited_subclass"].astype(str).str.strip() != ""]
    if len(sub):
        cnt = sub.groupby(["docdb_family_id", "cited_subclass"]).size().rename("n").reset_index()
        tot = cnt.groupby("docdb_family_id")["n"].transform("sum")
        cnt["s2"] = (cnt["n"] / tot) ** 2
        orig = (1.0 - cnt.groupby("docdb_family_id")["s2"].sum()).rename("originality")
    else:
        orig = pd.Series(dtype=float, name="originality")

    fams_dedup = df.drop_duplicates(["docdb_family_id", "cited_family"])
    tct = fams_dedup.groupby("docdb_family_id")["cite_age"].median().rename("tech_cycle_time")
    n_bwd = fams_dedup.groupby("docdb_family_id")["cited_family"].nunique().rename("n_bwd_cited_fams")
    return pd.concat([orig, tct, n_bwd], axis=1)


def compute_causal_recombination_novelty(
    fam_subclasses: pd.DataFrame,
    family_years: pd.Series,
) -> pd.DataFrame:
    """Compute Fleming (2001) / Verhoeven et al. (2016) Novelty in Recombination (NR) strictly causally.

    For each family, lists all unordered pairs of distinct 4-char subclasses (or CPC main groups)
    and computes the share of pairs whose FIRST appearance across the entire corpus is in `priority_year`.
    `fam_subclasses` must have columns: `docdb_family_id`, `code`.
    """
    if not len(fam_subclasses):
        return pd.DataFrame(columns=["n_code_pairs", "novel_pair_share_nr", "has_novel_pair_nr"])

    df = fam_subclasses[["docdb_family_id", "code"]].dropna().drop_duplicates().copy()
    df["year"] = df["docdb_family_id"].map(family_years)
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)

    # Group codes per family
    fam_codes = df.groupby("docdb_family_id")["code"].apply(lambda s: sorted(set(s.astype(str))))
    fam_yr_map = family_years.to_dict()

    first_seen: Dict[Tuple[str, str], int] = {}
    fam_pairs: Dict[int, List[Tuple[str, str]]] = {}

    for fid, codes in fam_codes.items():
        yr = fam_yr_map.get(fid)
        if yr is None or pd.isna(yr) or len(codes) < 2:
            continue
        yr_i = int(yr)
        # Cap combinations for rare mega-patents (>20 codes) to keep O(1) per family
        pairs = list(itertools.combinations(codes[:20], 2))
        fam_pairs[int(fid)] = pairs
        for p in pairs:
            prev = first_seen.get(p)
            if prev is None or yr_i < prev:
                first_seen[p] = yr_i

    rows = []
    for fid, pairs in fam_pairs.items():
        yr_i = int(fam_yr_map[fid])
        novel = sum(1 for p in pairs if first_seen[p] == yr_i)
        rows.append(
            {
                "docdb_family_id": fid,
                "n_code_pairs": len(pairs),
                "novel_pair_share_nr": novel / len(pairs),
                "has_novel_pair_nr": int(novel > 0),
            }
        )
    return pd.DataFrame(rows).set_index("docdb_family_id") if rows else pd.DataFrame(
        columns=["n_code_pairs", "novel_pair_share_nr", "has_novel_pair_nr"]
    )


def compute_causal_subfield_momentum(
    net_df: pd.DataFrame,
    year_col: str = "priority_year",
    group_col: str = "main_subclass",
    window: int = 3,
) -> pd.Series:
    """For each family filed in year t, compute strictly causal momentum of its subclass BEFORE year t:

    log1p(count in [t-window, t-1]) - log1p(count in [t-2*window, t-window-1]),
    minus the whole-universe log-growth over the same prior windows (excess subfield momentum).
    """
    counts = net_df.groupby([group_col, year_col]).size().unstack(fill_value=0)
    total_by_yr = net_df.groupby(year_col).size()
    years = sorted(int(y) for y in net_df[year_col].dropna().unique())

    momentum_lookup: Dict[Tuple[str, int], float] = {}
    for t in years:
        recent_yrs = [y for y in range(t - window, t) if y in counts.columns]
        prior_yrs = [y for y in range(t - 2 * window, t - window) if y in counts.columns]
        if not recent_yrs or not prior_yrs:
            continue
        tot_r = float(total_by_yr.reindex(recent_yrs).fillna(0).sum())
        tot_p = float(total_by_yr.reindex(prior_yrs).fillna(0).sum())
        base_growth = np.log1p(tot_r) - np.log1p(tot_p)

        sub_r = counts[recent_yrs].sum(axis=1).astype(float)
        sub_p = counts[prior_yrs].sum(axis=1).astype(float)
        excess = (np.log1p(sub_r) - np.log1p(sub_p)) - base_growth
        for sc, val in excess.items():
            momentum_lookup[(str(sc), t)] = float(val)

    return pd.Series(
        [momentum_lookup.get((str(sc), int(y)), np.nan) for sc, y in zip(net_df[group_col], net_df[year_col])],
        index=net_df.index,
        name="subfield_momentum",
    )


STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were", "into", "onto",
    "which", "wherein", "whereby", "thereof", "therein", "comprising", "comprises", "comprise",
    "including", "includes", "plurality", "least", "configured", "provided", "providing", "present",
    "invention", "disclosed", "disclosure", "embodiment", "embodiments", "method", "methods",
    "device", "devices", "apparatus", "system", "systems", "unit", "first", "second", "third",
    "one", "two", "having", "based", "said", "can", "may", "also", "used", "using", "through",
    "between", "each", "more", "than", "such", "when", "then", "has", "have", "been", "not",
}


def compute_arts_lexical_novelty(
    texts_df: pd.DataFrame,
    text_col: str = "text",
    year_col: str = "priority_year",
    lookback_years: int = 5,
) -> pd.DataFrame:
    """Zero-leakage lexical novelty (Arts, Hou & Gomez 2021) + readability complexity (Lai et al. 2026).

    Processes patents strictly chronologically by `priority_year`. A technical unigram or bigram
    in a year-t patent is novel if it did NOT appear in any patent during `[t - lookback_years, t - 1]`.
    Zero pretrained-model temporal leakage by construction!
    """
    tok_re = re.compile(r"[a-z]{3,}")
    df = texts_df[["docdb_family_id", year_col, text_col]].dropna(subset=[year_col]).copy()
    df[year_col] = df[year_col].astype(int)
    df = df.sort_values(year_col)

    vocab_by_year: Dict[int, set] = {}
    out_rows = []

    for yr, grp in df.groupby(year_col, sort=True):
        # Prior lookback vocabulary strictly BEFORE yr
        prior_vocab = set()
        for py in range(yr - lookback_years, yr):
            prior_vocab.update(vocab_by_year.get(py, ()))
        has_history = len(prior_vocab) > 0

        yr_vocab = set()
        for row in grp.itertuples(index=False):
            txt = str(getattr(row, text_col) or "").lower()
            raw_tokens = tok_re.findall(txt)
            tokens = [t for t in raw_tokens if t not in STOP_WORDS]
            bigrams = [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]
            terms = set(tokens) | set(bigrams)
            yr_vocab.update(terms)

            if has_history and terms:
                new_share = sum(1 for t in terms if t not in prior_vocab) / len(terms)
            else:
                new_share = np.nan

            # Readability / technical complexity proxy (Lai et al. 2026): avg word length & long-word share
            if raw_tokens:
                long_share = sum(1 for w in raw_tokens if len(w) >= 8) / len(raw_tokens)
                avg_wlen = float(np.mean([len(w) for w in raw_tokens]))
                word_count = len(raw_tokens)
            else:
                long_share, avg_wlen, word_count = np.nan, np.nan, 0

            out_rows.append(
                {
                    "docdb_family_id": int(row.docdb_family_id),
                    "priority_year": yr,
                    "arts_lexical_novelty": new_share,
                    "abstract_long_word_share": long_share,
                    "abstract_avg_word_len": avg_wlen,
                    "abstract_word_count": word_count,
                }
            )
        vocab_by_year[yr] = yr_vocab

    res = pd.DataFrame(out_rows).set_index("docdb_family_id")
    res["arts_novelty_rank_in_year"] = res.groupby("priority_year")["arts_lexical_novelty"].rank(pct=True)
    return res


# ---------------------------------------------------------------------------
# 3. Dynamic t0+2y Network Metrics (Age-Rescaled PageRank, CD Index, Generality)
# ---------------------------------------------------------------------------
def compute_dynamic_network_at_age(
    fwd_edges: pd.DataFrame,
    bwd_edges: pd.DataFrame,
    family_years: pd.Series,
    age_limit: int = 2,
) -> pd.DataFrame:
    """Compute strictly point-in-time dynamic network signals at `priority_year + age_limit`:

    - `early_cites`: forward citations received within `age_limit` years
    - `pagerank_age_ratio`: Age-Rescaled PageRank (Mariani et al. 2019) on citations up to `t + age_limit`
    - `cd_index`: Funk & Owen-Smith (2017) disruption index computed on citations up to `t + age_limit`
    """
    fids = [int(i) for i in family_years.index]
    yr_map = {int(k): int(v) for k, v in family_years.dropna().items()}

    # Filter forward citations to those arriving within age_limit of cited family's priority year
    if len(fwd_edges):
        fe = fwd_edges[["citing_family", "docdb_family_id", "citing_year"]].dropna().copy()
        fe["cited_year"] = fe["docdb_family_id"].map(yr_map)
        fe = fe.dropna(subset=["cited_year"])
        fe = fe[(fe["citing_family"] != fe["docdb_family_id"]) & (fe["citing_year"] <= fe["cited_year"] + age_limit)]
    else:
        fe = pd.DataFrame(columns=["citing_family", "docdb_family_id", "citing_year", "cited_year"])

    early_cites = fe.groupby("docdb_family_id")["citing_family"].nunique().reindex(fids).fillna(0.0)

    # PageRank on the early citation graph
    G = nx.DiGraph()
    G.add_nodes_from(fids)
    if len(fe):
        G.add_edges_from(zip(fe["citing_family"].astype(int), fe["docdb_family_id"].astype(int)))
    pr = nx.pagerank(G, alpha=0.85, max_iter=150, tol=1e-6)
    pr_s = pd.Series({fid: pr.get(fid, 0.0) for fid in fids}, name="pr_raw")

    # Age-rescaled PageRank by priority year (Mariani et al. 2019)
    pr_df = pd.DataFrame({"priority_year": family_years.reindex(fids), "pr_raw": pr_s})
    mu = pr_df.groupby("priority_year")["pr_raw"].transform("mean")
    pr_ratio = pd.Series(np.where(mu > 0, pr_df["pr_raw"] / mu, 1.0), index=fids, name=f"pagerank_age_ratio_{age_limit}y")

    # CD index (Funk & Owen-Smith 2017): for each focal family i with backward refs B_i and early forward citers F_i
    # n_i = citers of i that do NOT cite any b in B_i; n_j = citers of i that ALSO cite >=1 b in B_i
    # Simplified local CD = (n_i - n_j) / (n_i + n_j) when n_i + n_j > 0 else NaN
    bwd_map: Dict[int, set] = {}
    if len(bwd_edges):
        be = bwd_edges[["docdb_family_id", "cited_family"]].dropna().drop_duplicates()
        for fid, grp in be.groupby("docdb_family_id")["cited_family"]:
            bwd_map[int(fid)] = set(grp.astype(int))

    # Map each citing family -> set of families it cites (from both fwd_edges and bwd_edges)
    citer_refs: Dict[int, set] = {}
    if len(fe):
        for cf, grp in fe.groupby("citing_family")["docdb_family_id"]:
            citer_refs.setdefault(int(cf), set()).update(grp.astype(int))
    for fid, refs in bwd_map.items():
        citer_refs.setdefault(fid, set()).update(refs)

    cd_vals: Dict[int, float] = {}
    if len(fe):
        for focal, grp in fe.groupby("docdb_family_id")["citing_family"]:
            focal_i = int(focal)
            refs = bwd_map.get(focal_i, set())
            if not refs:
                continue
            citers = set(grp.astype(int))
            ni = sum(1 for c in citers if not (citer_refs.get(c, set()) & refs))
            nj = len(citers) - ni
            if (ni + nj) > 0:
                cd_vals[focal_i] = (ni - nj) / float(ni + nj)

    cd_s = pd.Series({fid: cd_vals.get(fid, np.nan) for fid in fids}, name=f"cd_index_{age_limit}y")
    return pd.DataFrame(
        {
            f"early_cites_{age_limit}y": early_cites,
            f"pagerank_age_ratio_{age_limit}y": pr_ratio,
            f"cd_index_{age_limit}y": cd_s,
        },
        index=fids,
    )


# ---------------------------------------------------------------------------
# 4. Rolling Out-of-Time Backtest, Metrics (PR-AUC, P@K, Lift) & Rule Scorecard
# ---------------------------------------------------------------------------
def precision_recall_lift_at_k(y_true: np.ndarray, scores: np.ndarray, share: float = 0.10) -> Dict[str, float]:
    """Compute PR-AUC, ROC-AUC, Precision@TopK, Recall@TopK, and Lift@TopK (Theory 6, p. 36)."""
    y = np.asarray(y_true, dtype=int)
    s = np.asarray(scores, dtype=float)
    valid = np.isfinite(s)
    y, s = y[valid], s[valid]
    n = len(y)
    if n == 0 or y.sum() == 0 or y.sum() == n:
        return {"PR_AUC": np.nan, "ROC_AUC": np.nan, "P_at_10pct": np.nan, "R_at_10pct": np.nan, "Lift_at_10pct": np.nan, "base_rate": np.nan}

    base_rate = float(y.mean())
    k = max(1, int(round(share * n)))
    top_idx = np.argsort(-s, kind="mergesort")[:k]
    p_at_k = float(y[top_idx].mean())
    r_at_k = float(y[top_idx].sum() / y.sum())
    return {
        "PR_AUC": float(average_precision_score(y, s)),
        "ROC_AUC": float(roc_auc_score(y, s)),
        "P_at_10pct": p_at_k,
        "R_at_10pct": r_at_k,
        "Lift_at_10pct": p_at_k / base_rate if base_rate > 0 else np.nan,
        "base_rate": base_rate,
    }


def bootstrap_metric_ci(
    y_true: np.ndarray,
    scores: np.ndarray,
    metric_key: str = "PR_AUC",
    n_boot: int = 400,
    seed: int = 34,
) -> Tuple[float, float, float]:
    """Point estimate and 95% bootstrap CI for any metric returned by `precision_recall_lift_at_k`."""
    y = np.asarray(y_true, dtype=int)
    s = np.asarray(scores, dtype=float)
    pt = precision_recall_lift_at_k(y, s)[metric_key]
    rng = np.random.default_rng(seed)
    vals = []
    n = len(y)
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        yb = y[idx]
        if yb.sum() == 0 or yb.sum() == n:
            continue
        vals.append(precision_recall_lift_at_k(yb, s[idx])[metric_key])
    if not vals:
        return pt, np.nan, np.nan
    return pt, float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def make_classifiers(random_state: int = 34) -> Dict[str, object]:
    """Interpretable Logistic Regression + Random Forest + HistGradientBoosting."""
    logistic = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
            ("scale", StandardScaler()),
            ("model", LogisticRegression(max_iter=2000, C=0.5, class_weight="balanced", random_state=random_state)),
        ]
    )
    rf = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
            ("model", RandomForestClassifier(n_estimators=250, max_depth=8, min_samples_leaf=15, class_weight="balanced_subsample", random_state=random_state, n_jobs=-1)),
        ]
    )
    hgb = HistGradientBoostingClassifier(
        max_iter=250,
        learning_rate=0.04,
        max_leaf_nodes=23,
        min_samples_leaf=30,
        l2_regularization=1.0,
        class_weight="balanced",
        random_state=random_state,
    )
    return {"logistic": logistic, "random_forest": rf, "boosting": hgb}


def rule_based_future_score(
    features_df: pd.DataFrame,
    directions: Dict[str, int],
    year_series: Optional[pd.Series] = None,
) -> pd.Series:
    """Zero-training Rule-Based Future Scorecard (Theory 6, pp. 16 & 25): equal-weighted within-year percentile ranks."""
    cols = [c for c in directions if c in features_df.columns]
    if not cols:
        return pd.Series(np.nan, index=features_df.index, name="rule_based_score")

    ranked = pd.DataFrame(index=features_df.index)
    for c in cols:
        s = features_df[c].astype(float) * float(directions[c])
        if year_series is not None:
            ranked[c] = s.groupby(year_series).rank(pct=True)
        else:
            ranked[c] = s.rank(pct=True)
    return ranked.mean(axis=1).rename("rule_based_score")


def run_rolling_oot_backtest(
    X: pd.DataFrame,
    y: pd.Series,
    years: pd.Series,
    in_sector: pd.Series,
    feature_sets: Dict[str, List[str]],
    test_years: Sequence[int],
    lookback: int = 5,
    random_state: int = 34,
) -> pd.DataFrame:
    """Strict rolling out-of-time backtest: for each T in `test_years`, train strictly on [T-lookback, T-1], test on T."""
    preds = []
    for T in test_years:
        tr_mask = years.between(T - lookback, T - 1) & y.notna()
        te_mask = (years == T) & y.notna()
        if tr_mask.sum() < 50 or te_mask.sum() < 20 or y[tr_mask].nunique() < 2:
            continue
        y_tr = y[tr_mask].astype(int)
        y_te = y[te_mask].astype(int)

        for set_name, cols in feature_sets.items():
            cols_ok = [c for c in cols if c in X.columns]
            if not cols_ok:
                continue
            for model_name, clf in make_classifiers(random_state=random_state).items():
                clf.fit(X.loc[tr_mask, cols_ok], y_tr)
                prob = clf.predict_proba(X.loc[te_mask, cols_ok])[:, 1]
                preds.append(
                    pd.DataFrame(
                        {
                            "docdb_family_id": X.index[te_mask],
                            "test_year": T,
                            "feature_set": set_name,
                            "model": model_name,
                            "score": prob,
                            "y": y_te.to_numpy(),
                            "in_sector": in_sector.loc[te_mask].to_numpy(dtype=bool),
                        }
                    )
                )
    return pd.concat(preds, ignore_index=True) if preds else pd.DataFrame()


# ---------------------------------------------------------------------------
# 5. Firm-Level Aggregation (Theory 6, p. 38)
# ---------------------------------------------------------------------------
def aggregate_firm_future_scores(
    family_scores: pd.DataFrame,
    firm_col: str = "firm",
    prob_col: str = "pred_prob",
    rule_col: Optional[str] = "rule_score",
    top_k: int = 3,
    top_thresh: Optional[float] = None,
) -> pd.DataFrame:
    """Aggregate patent-level future predictions to the firm level under 3 Theory 6 (p. 38) perspectives:

    1. Mean predicted probability (average portfolio quality)
    2. Expected breakthroughs: sum(pred_prob) (scale x quality)
    3. Top-3 mean probability & top-decile share (breakthrough concentration for Electrolux M&A)
    """
    df = family_scores.dropna(subset=[firm_col, prob_col]).copy()
    if not len(df):
        return pd.DataFrame()
    if top_thresh is None:
        top_thresh = float(df[prob_col].quantile(0.90))

    rows = []
    for firm, g in df.groupby(firm_col):
        p = np.sort(g[prob_col].to_numpy(dtype=float))[::-1]
        n = len(p)
        row = {
            "firm": firm,
            "recent_families": n,
            "mean_prob": float(np.mean(p)),
            "expected_breakthroughs": float(np.sum(p)),
            "top3_mean_prob": float(np.mean(p[: min(top_k, n)])),
            "share_top_decile (%)": float((p >= top_thresh).mean() * 100.0),
        }
        if rule_col and rule_col in g.columns:
            row["rule_based_mean"] = float(g[rule_col].mean())
        rows.append(row)

    out = pd.DataFrame(rows).set_index("firm")
    # Composite 0-100 Future Score (50% average quality + 50% breakthrough concentration, scaled 0-100)
    # Kept transparent and comparable across both small focused visionaries and large filers
    q_rank = out["mean_prob"].rank(pct=True)
    b_rank = out["top3_mean_prob"].rank(pct=True)
    e_rank = out["expected_breakthroughs"].rank(pct=True)
    out["future_score_quality_breakthrough"] = (0.40 * q_rank + 0.35 * b_rank + 0.25 * e_rank) * 100.0
    return out.sort_values("future_score_quality_breakthrough", ascending=False)
