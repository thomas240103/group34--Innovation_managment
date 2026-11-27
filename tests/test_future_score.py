"""Unit tests for src/future_score.py (Step 4 · Future Score engine)."""
import numpy as np
import pandas as pd
import pytest

from future_score import (
    aggregate_firm_future_scores,
    compute_arts_lexical_novelty,
    compute_causal_recombination_novelty,
    compute_causal_subfield_momentum,
    compute_dynamic_network_at_age,
    compute_originality_and_tct,
    label_top_decile_by_cohort,
    precision_recall_lift_at_k,
    rule_based_future_score,
    run_rolling_oot_backtest,
)


def test_label_top_decile_by_cohort():
    df = pd.DataFrame(
        {
            "priority_year": [2015] * 40,
            "main_subclass": ["B25J"] * 40,
            "fwd_cites_5y": list(range(40)),
        }
    )
    y, cohort = label_top_decile_by_cohort(df, top_share=0.10, min_cohort=20)
    assert y.sum() == 4
    assert y.iloc[-1] == 1 and y.iloc[0] == 0
    assert (cohort == "2015|B25J").all()


def test_originality_tct_and_recombination():
    fy = pd.Series({1: 2015, 2: 2016, 3: 2017})
    bwd = pd.DataFrame(
        {
            "docdb_family_id": [1, 1, 2, 2],
            "cited_family": [10, 11, 12, 13],
            "cited_subclass": ["B25J", "G05D", "B25J", "B25J"],
            "cited_year": [2010, 2012, 2014, 2014],
        }
    )
    ot = compute_originality_and_tct(bwd, fy)
    assert ot.loc[1, "originality"] == pytest.approx(0.5)
    assert ot.loc[2, "originality"] == pytest.approx(0.0)
    assert ot.loc[1, "tech_cycle_time"] == pytest.approx(4.0)

    # Recombination NR: (B25J, G05D) first appears in 2015 -> novel in 2015, NOT novel in 2016
    fc = pd.DataFrame({"docdb_family_id": [1, 1, 2, 2, 3, 3], "code": ["B25J", "G05D", "B25J", "G05D", "B25J", "G06N"]})
    nr = compute_causal_recombination_novelty(fc, fy)
    assert nr.loc[1, "novel_pair_share_nr"] == pytest.approx(1.0)
    assert nr.loc[2, "novel_pair_share_nr"] == pytest.approx(0.0)
    assert nr.loc[3, "novel_pair_share_nr"] == pytest.approx(1.0)


def test_causal_momentum_and_arts_novelty():
    rows = []
    # B25J stays flat, G05D doubles before 2018
    for y in range(2012, 2015):
        rows += [{"priority_year": y, "main_subclass": "B25J"}] * 10
        rows += [{"priority_year": y, "main_subclass": "G05D"}] * 2
    for y in range(2015, 2018):
        rows += [{"priority_year": y, "main_subclass": "B25J"}] * 10
        rows += [{"priority_year": y, "main_subclass": "G05D"}] * 10
    rows += [{"priority_year": 2018, "main_subclass": "B25J"}, {"priority_year": 2018, "main_subclass": "G05D"}]
    net = pd.DataFrame(rows)
    mom = compute_causal_subfield_momentum(net, window=3)
    assert mom.iloc[-1] > mom.iloc[-2]  # G05D momentum > B25J momentum in 2018

    texts = pd.DataFrame(
        {
            "docdb_family_id": [1, 2, 3],
            "priority_year": [2015, 2016, 2016],
            "text": [
                "humanoid robot walking leg actuator joint",
                "humanoid robot walking leg actuator joint",
                "neuromorphic tactile tendon reinforcement gait",
            ],
        }
    )
    arts = compute_arts_lexical_novelty(texts, lookback_years=5)
    assert pd.isna(arts.loc[1, "arts_lexical_novelty"])  # first year has no prior history
    assert arts.loc[3, "arts_lexical_novelty"] > arts.loc[2, "arts_lexical_novelty"]


def test_dynamic_network_and_rolling_backtest():
    fy = pd.Series({1: 2012, 2: 2013, 3: 2014, 4: 2014})
    fwd = pd.DataFrame({"citing_family": [2, 3, 4], "docdb_family_id": [1, 1, 2], "citing_year": [2013, 2014, 2014]})
    bwd = pd.DataFrame({"docdb_family_id": [2, 3], "cited_family": [1, 1]})
    dyn = compute_dynamic_network_at_age(fwd, bwd, fy, age_limit=2)
    assert dyn.loc[1, "early_cites_2y"] == 2
    assert dyn.loc[1, "pagerank_age_ratio_2y"] > 0

    # Synthetic OOT backtest with clear signal
    rng = np.random.default_rng(42)
    n = 600
    yrs = pd.Series(rng.integers(2010, 2017, size=n), index=range(n))
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    prob = 1.0 / (1.0 + np.exp(-(2.0 * x1 + 0.5 * x2 - 2.0)))
    y = pd.Series((rng.random(n) < prob).astype(int), index=range(n))
    X = pd.DataFrame({"f1": x1, "f2": x2}, index=range(n))
    in_sec = pd.Series(rng.random(n) < 0.2, index=range(n))

    preds = run_rolling_oot_backtest(
        X, y, yrs, in_sec, feature_sets={"benchmark": ["f2"], "proposed": ["f1", "f2"]}, test_years=[2015, 2016], lookback=4
    )
    assert len(preds) > 0
    m_bench = precision_recall_lift_at_k(
        preds.loc[(preds["feature_set"] == "benchmark") & (preds["model"] == "logistic"), "y"],
        preds.loc[(preds["feature_set"] == "benchmark") & (preds["model"] == "logistic"), "score"],
    )
    m_prop = precision_recall_lift_at_k(
        preds.loc[(preds["feature_set"] == "proposed") & (preds["model"] == "logistic"), "y"],
        preds.loc[(preds["feature_set"] == "proposed") & (preds["model"] == "logistic"), "score"],
    )
    assert m_prop["PR_AUC"] > m_bench["PR_AUC"]

    rb = rule_based_future_score(X, {"f1": +1, "f2": +1}, year_series=yrs)
    assert rb.notna().all()

    f_scores = pd.DataFrame({"firm": ["A", "A", "A", "B", "B"], "pred_prob": [0.9, 0.8, 0.7, 0.2, 0.1], "rule_score": [0.8, 0.8, 0.7, 0.3, 0.2]})
    agg = aggregate_firm_future_scores(f_scores)
    assert agg.index[0] == "A"
    assert agg.loc["A", "expected_breakthroughs"] == pytest.approx(2.4)
