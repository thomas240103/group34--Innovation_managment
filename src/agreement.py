"""Agreement between two readers of the same families (Step 0, Section 5.24): Cohen's kappa with a bootstrap CI."""
from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd


def cohen_kappa(a, b) -> float:
    """Cohen's kappa (1960) between two lists of labels of the same items (missing pairs dropped)."""
    d = pd.DataFrame({"a": list(a), "b": list(b)}).dropna()
    if not len(d):
        return np.nan
    cats = sorted(set(d["a"]) | set(d["b"]))
    po = float((d["a"] == d["b"]).mean())
    pa = d["a"].value_counts(normalize=True).reindex(cats).fillna(0)
    pb = d["b"].value_counts(normalize=True).reindex(cats).fillna(0)
    pe = float((pa * pb).sum())
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def kappa_with_ci(a, b, n_boot: int = 2000, seed: int = 34) -> Dict[str, float]:
    """Kappa, raw agreement and a bootstrap 95% CI (items resampled)."""
    d = pd.DataFrame({"a": list(a), "b": list(b)}).dropna().reset_index(drop=True)
    k = cohen_kappa(d["a"], d["b"])
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        s = d.iloc[rng.integers(0, len(d), size=len(d))]
        vals.append(cohen_kappa(s["a"], s["b"]))
    vals = [v for v in vals if np.isfinite(v)]
    lo, hi = (np.percentile(vals, [2.5, 97.5]) if vals else (np.nan, np.nan))
    return {"kappa": float(k), "ci_low": float(lo), "ci_high": float(hi),
            "agreement": float((d["a"] == d["b"]).mean()) if len(d) else np.nan, "items": int(len(d))}
