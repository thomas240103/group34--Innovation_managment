"""Tests for src/quadrant.py, the review-fix helpers of src/future_score.py, src/nowcast.py, src/domains.py
and src/agreement.py."""
import numpy as np
import pandas as pd
import pytest

from agreement import cohen_kappa, kappa_with_ci
from domains import domains_of, family_domains
from future_score import (
    adversarial_validation_auc,
    fit_isotonic_calibrator,
    label_top_decile_hierarchical,
    paired_bootstrap_diff,
    population_stability_index,
    reliability_table,
    spearman_with_ci,
)
from nowcast import completeness_by_year, nowcast_counts, publication_delays
from quadrant import (
    combine_rrf,
    common_future_scores,
    depreciation_weight,
    family_today_table,
    firm_today_indicators,
    hierarchical_cohort_mean,
    quadrant_label,
    shrink_mean,
)


# ---------------------------------------------------------------- quadrant: present "today"
def _toy():
    fams = pd.DataFrame({"docdb_family_id": [1, 2, 3, 4, 5, 6],
                         "priority_year": [2005, 2010, 2020, 2020, 2024, 2024]})
    apps = pd.DataFrame({
        "docdb_family_id": [1, 1, 2, 3, 3, 3, 4, 5, 6],
        "appln_id": range(9),
        "appln_auth": ["JP", "US", "JP", "CN", "WO", "US", "CN", "CN", "US"],
        "appln_kind": ["A"] * 9,
        "appln_filing_year": [2005, 2006, 2010, 2020, 2020, 2021, 2020, 2024, 2024],
        "appln_filing_date": ["2005-01-01", "2006-01-01", "2010-01-01", "2020-01-01", "2020-06-01",
                              "2021-01-01", "2020-03-01", "2024-01-01", "2024-02-01"],
        "granted": ["Y", "Y", "N", "Y", "N", "Y", "N", "N", "N"],
    })
    fwd = pd.DataFrame({"docdb_family_id": [1, 1, 3, 3, 3, 4], "citing_family": [10, 11, 12, 13, 14, 15]})
    alive = pd.Series({1: False, 2: False, 3: True, 4: True, 5: True, 6: True})
    return fams, apps, fwd, alive


def test_family_today_table_and_firm_indicators():
    fams, apps, fwd, alive = _toy()
    t = family_today_table(fams, apps, fwd, alive, reference_year=2026, delta=0.15,
                           influence_last_year=2024, globalization_last_year=2024, success_last_year=2021, min_cohort=1)
    assert t.loc[1, "stock_weight"] == 0.0                      # lapsed: no weight in the living stock
    assert t.loc[3, "stock_weight"] == pytest.approx(0.85 ** 6)
    assert bool(t.loc[3, "has_pct"]) and t.loc[3, "offices"] == 2
    assert t.loc[3, "first_office"] == "CN" and t.loc[6, "first_office"] == "US"
    # family 3 has 3 citations, family 4 one: same year, same office group (CN) -> 1.5 and 0.5
    assert t.loc[3, "influence_rel"] == pytest.approx(1.5)
    assert t.loc[4, "influence_rel"] == pytest.approx(0.5)

    ff = pd.DataFrame({"docdb_family_id": [1, 2, 3, 4, 5, 6], "firm": ["OLD", "OLD", "NEW", "NEW", "NEW", "YOUNG"]})
    ind = firm_today_indicators(t, ff, ["OLD", "NEW", "YOUNG"], min_families=1)
    assert ind.loc["OLD", "Volume"] == 0.0                     # everything lapsed
    assert ind[["Volume"]].sum().iloc[0] == pytest.approx(100.0)
    assert ind.loc["NEW", "Volume"] > ind.loc["YOUNG", "Volume"]
    assert ind.loc["YOUNG", "families"] == 1


def test_min_families_blanks_indicators():
    fams, apps, fwd, alive = _toy()
    t = family_today_table(fams, apps, fwd, alive, reference_year=2026, min_cohort=1)
    ind = firm_today_indicators(t, pd.DataFrame({"docdb_family_id": [6], "firm": ["X"]}), ["X"], min_families=5)
    assert np.isnan(ind.loc["X", "Influence"]) and ind.loc["X", "Volume"] > 0


def test_hierarchical_cohort_mean_falls_back():
    df = pd.DataFrame({"y": [2020] * 4, "o": ["CN", "CN", "CN", "US"], "v": [1.0, 2.0, 3.0, 10.0]})
    m = hierarchical_cohort_mean(df, "v", [["y", "o"], ["y"]], min_cohort=3)
    assert m.iloc[0] == pytest.approx(2.0)                     # CN cohort has 3 rows
    assert m.iloc[3] == pytest.approx(4.0)                     # US alone too small: whole year


def test_depreciation_weight():
    w = depreciation_weight(pd.Series([2026, 2025, 2030]), 2026, 0.5)
    assert list(w) == [1.0, 0.5, 1.0]


def test_combine_rrf_missing_and_min():
    t = pd.DataFrame({"A": [3.0, 2.0, 1.0], "B": [1.0, np.nan, 3.0]}, index=["x", "y", "z"])
    r = combine_rrf(t, {"A": 0.5, "B": 0.5}, min_indicators=1)
    assert r.loc["y", "indicators used"] == 1 and bool(r.loc["y", "provisional"])
    r2 = combine_rrf(t, {"A": 0.5, "B": 0.5}, min_indicators=2)
    assert np.isnan(r2.loc["y", "score"]) and not np.isnan(r2.loc["x", "score"])


# ---------------------------------------------------------------- quadrant: future on the common set
def test_shrink_and_common_future_scores():
    s = shrink_mean(pd.Series([0.9, 0.9]), pd.Series([1, 100]), prior=0.1, strength=10)
    assert s.iloc[0] < s.iloc[1] and s.iloc[1] > 0.8

    probs = pd.DataFrame({"docdb_family_id": [1, 2, 3, 4, 5], "firm": ["A", "A", "A", "B", "C"],
                          "prob": [0.3, 0.4, 0.5, 0.9, 0.2]})
    allf = pd.DataFrame({"docdb_family_id": [1, 2, 3, 4, 5, 6, 7], "firm": ["A", "A", "A", "B", "C", "OLD", "OLD"]})
    out = common_future_scores(probs, ["A", "B", "C", "OLD"], allf, prior=0.1, strength=10)
    assert out.loc["OLD", "future_score"] == 0.0 and bool(out.loc["OLD", "no recent families"])
    assert out.loc["A", "expected breakthroughs"] == pytest.approx(1.2)
    assert out.loc["A", "mean prob (shrunk)"] < 0.4            # pulled towards the prior
    assert set(out.index) == {"A", "B", "C", "OLD"}


def test_quadrant_label():
    assert quadrant_label(80, 80, 50, 50) == "Leader"
    assert quadrant_label(80, 10, 50, 50) == "Challenger"
    assert quadrant_label(10, 80, 50, 50) == "Visionary"
    assert quadrant_label(10, 10, 50, 50) == "Niche player"
    assert quadrant_label(np.nan, 10, 50, 50) == "not placed"


# ---------------------------------------------------------------- future_score review fixes
def test_label_top_decile_hierarchical_uses_office():
    df = pd.DataFrame({"priority_year": [2015] * 60, "main_subclass": ["B25J"] * 60,
                       "first_office_group": ["CN"] * 30 + ["other"] * 30,
                       "fwd_cites_5y": list(range(100, 130)) + list(range(0, 30))})
    y, cohort = label_top_decile_hierarchical(df, min_cohort=30)
    # without the office, the top decile would be all CN; with it, each office has its own top
    assert y[df["first_office_group"] == "other"].sum() >= 3
    assert cohort.nunique() == 2


def test_paired_bootstrap_diff():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 400)
    good = y + rng.normal(0, 0.5, 400)
    bad = rng.normal(0, 1, 400)
    r = paired_bootstrap_diff(y, bad, good, n_boot=200)
    assert r["diff"] > 0 and r["ci_low"] > 0 and r["p_not_better"] < 0.05


def test_calibration_and_reliability():
    rng = np.random.default_rng(1)
    s = rng.uniform(0, 1, 2000)
    y = (rng.uniform(0, 1, 2000) < s * 0.2).astype(int)        # true probability = 0.2 * score
    iso = fit_isotonic_calibrator(y, s)
    p = iso.predict(s)
    tab, ece, brier = reliability_table(y, p, n_bins=10)
    assert len(tab) == 10 and ece < 0.05 and 0 <= brier < 0.2
    _, ece_raw, _ = reliability_table(y, s, n_bins=10)
    assert ece_raw > ece                                          # the raw score was far from a probability


def test_psi_and_adversarial():
    rng = np.random.default_rng(2)
    a = pd.Series(rng.normal(0, 1, 1000))
    assert population_stability_index(a, pd.Series(rng.normal(0, 1, 1000))) < 0.1
    assert population_stability_index(a, pd.Series(rng.normal(2, 1, 1000))) > 0.25
    X1 = pd.DataFrame({"f": rng.normal(0, 1, 300)})
    X2 = pd.DataFrame({"f": rng.normal(3, 1, 300)})
    assert adversarial_validation_auc(X1, X2) > 0.9


def test_spearman_with_ci():
    x = pd.Series(range(20), dtype=float)
    r = spearman_with_ci(x, x * 2 + 1, n_boot=100)
    assert r["rho"] == pytest.approx(1.0) and r["firms"] == 20


# ---------------------------------------------------------------- nowcast
def test_nowcast():
    delays = np.full(100, 550.0)                                 # every family published 550 days after priority
    comp = completeness_by_year(delays, [2020, 2025], "2026-10-31")
    assert comp[2020] == pytest.approx(1.0)
    assert 0 < comp[2025] < 0.5
    obs = pd.DataFrame({"priority_year": [2020, 2025], "families": [100, 20]})
    nc = nowcast_counts(obs, pd.DataFrame({"delay_days": delays}), "2026-10-31", n_boot=20)
    assert nc.loc[nc["priority_year"] == 2020, "nowcast"].iloc[0] == pytest.approx(100)
    assert nc.loc[nc["priority_year"] == 2025, "nowcast"].iloc[0] > 20
    fam = pd.DataFrame({"priority_date": ["2020-01-01", "2020-01-01"], "first_publn_date": ["2021-07-01", "9999-12-31"]})
    assert len(publication_delays(fam)) == 1


# ---------------------------------------------------------------- domains
def test_domains():
    assert domains_of("A household service humanoid robot for kitchen cooking") == ["home"]
    assert "home" not in domains_of("Method for returning the joint to the home position")
    assert "industry and logistics" in domains_of("Humanoid robot for factory assembly line")
    assert domains_of("A humanoid robot joint") == []
    assert "home" in domains_of("家用人形机器人")
    fd = family_domains(pd.DataFrame({"docdb_family_id": [1, 2], "text": ["elderly care at home", "a joint"]}))
    assert fd.groupby("docdb_family_id")["weight"].sum().tolist() == [1.0, 1.0]
    assert fd.loc[fd["docdb_family_id"] == 2, "domain"].tolist() == ["unspecified"]


# ---------------------------------------------------------------- agreement
def test_kappa():
    assert cohen_kappa([1, 0, 1, 0], [1, 0, 1, 0]) == pytest.approx(1.0)
    assert cohen_kappa([1, 1, 0, 0], [1, 0, 1, 0]) == pytest.approx(0.0)
    r = kappa_with_ci([1, 1, 0, 0, 1, 0] * 5, [1, 1, 0, 1, 1, 0] * 5, n_boot=200)
    assert 0 < r["kappa"] < 1 and r["items"] == 30


# ---------------------------------------------------------------- config/sector.yaml agrees with the rule and Step 3
def test_config_consistent():
    import ast
    import json
    from pathlib import Path

    from config import load_config
    from sector_rule import load_rule

    cfg, rule = load_config(), load_rule()
    for k in ("year_min", "year_max", "last_complete_year"):
        assert cfg["window"][k] == rule["window"][k]
    root = Path(__file__).resolve().parents[1]
    nb = json.load(open(root / "step3_present_score.ipynb", encoding="utf-8"))
    code = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    weights = None
    for line in code.split("\n"):
        if line.startswith("WEIGHTS = {"):
            weights = ast.literal_eval(line.split("=", 1)[1].strip())
    assert weights == cfg["present_score"]["weights"], "Step 3 WEIGHTS and config/sector.yaml differ"
