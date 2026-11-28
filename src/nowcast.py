"""Nowcasting the incomplete priority years (Step 1, Section 7.3).

A family enters PATSTAT only once it is published, about 18 months after its first priority, and the delay differs by
office. So the count of a recent priority year is a fraction of its final value. We estimate that fraction from the
publication delays of families whose years are complete:

    completeness(y) = mean over the days d of year y of  F(cut_date - d),

where F is the empirical distribution of the delay "first publication - first priority" (by group, e.g. office of
first filing), and cut_date is the last publication date in the data. The nowcast is observed / completeness.
A bootstrap of the delays gives an interval. This corrects the publication lag only: a family published but not yet
loaded in PATSTAT, or a change in filing behaviour, is not corrected.
"""
from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd


def publication_delays(families: pd.DataFrame, prio_col: str = "priority_date", publn_col: str = "first_publn_date",
                       group_col: Optional[str] = None) -> pd.DataFrame:
    """Delay in days between first priority and first publication, one row per family (non-negative, known dates)."""
    d = families.copy()
    d["prio"] = pd.to_datetime(d[prio_col], errors="coerce")
    d["publn"] = pd.to_datetime(d[publn_col], errors="coerce")
    d = d[(d["prio"].dt.year < 9000) & (d["publn"].dt.year < 9000)]
    d["delay_days"] = (d["publn"] - d["prio"]).dt.days
    d = d[d["delay_days"] >= 0]
    cols = ["delay_days"] + ([group_col] if group_col else [])
    return d[cols]


def completeness_by_year(delays: np.ndarray, years, cut_date) -> pd.Series:
    """Expected share of a priority year's families already published at `cut_date` (uniform days in the year)."""
    delays = np.sort(np.asarray(delays, dtype=float))
    cut = pd.Timestamp(cut_date)
    out = {}
    for y in years:
        days = pd.date_range(f"{int(y)}-01-01", f"{int(y)}-12-31", freq="D")
        horizon = (cut - days).days.to_numpy(dtype=float)
        frac = np.searchsorted(delays, horizon, side="right") / max(len(delays), 1)
        out[int(y)] = float(np.mean(np.where(horizon < 0, 0.0, frac)))
    return pd.Series(out, name="completeness")


def nowcast_counts(
    observed: pd.DataFrame,
    delays: pd.DataFrame,
    cut_date,
    group_col: Optional[str] = None,
    n_boot: int = 300,
    seed: int = 34,
    min_completeness: float = 0.05,
) -> pd.DataFrame:
    """Nowcast of the families of each priority year, with a bootstrap 90% interval.

    observed: one row per (year[, group]) with column `families`.
    delays: output of publication_delays (with the same group column, if any).
    A year whose completeness is below `min_completeness` is not nowcast (the correction would be a guess).
    """
    rng = np.random.default_rng(seed)
    groups = [None] if group_col is None else sorted(observed[group_col].dropna().unique())
    rows = []
    for g in groups:
        obs = observed if g is None else observed[observed[group_col] == g]
        dl = delays["delay_days"].to_numpy() if g is None else delays.loc[delays[group_col] == g, "delay_days"].to_numpy()
        if not len(dl):
            dl = delays["delay_days"].to_numpy()          # no delays for this group: use all
        years = obs["priority_year"].astype(int).tolist()
        comp = completeness_by_year(dl, years, cut_date)
        boots = np.array([completeness_by_year(rng.choice(dl, size=len(dl), replace=True), years, cut_date).to_numpy()
                          for _ in range(n_boot)]) if n_boot else None
        for i, (_, r) in enumerate(obs.iterrows()):
            y = int(r["priority_year"])
            c = comp[y]
            ok = c >= min_completeness
            row = {"priority_year": y, "observed": float(r["families"]), "completeness": c,
                   "nowcast": r["families"] / c if ok else np.nan}
            if boots is not None and ok:
                nc = r["families"] / np.clip(boots[:, i], min_completeness, None)
                row["nowcast_p05"], row["nowcast_p95"] = np.percentile(nc, [5, 95])
            if g is not None:
                row[group_col] = g
            rows.append(row)
    out = pd.DataFrame(rows)
    if group_col is not None:
        agg = {"observed": "sum", "nowcast": lambda s: s.sum(min_count=len(s))}
        if "nowcast_p05" in out:
            agg.update({"nowcast_p05": "sum", "nowcast_p95": "sum"})     # sum of group bounds: a conservative band
        tot = out.groupby("priority_year").agg(agg)
        tot["completeness"] = tot["observed"] / tot["nowcast"]
        return tot.reset_index()
    return out
