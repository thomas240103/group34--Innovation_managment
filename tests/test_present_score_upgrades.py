"""Unit tests for src/present_score_upgrades.py (Step 3 SOTA upgrades)."""
import numpy as np
import pandas as pd
import pytest

from present_score_upgrades import (
    compute_age_rescaled_pagerank,
    compute_causal_science_proximity,
    compute_living_and_residual_life,
    compute_patent_asset_index,
    jaffe_cpc_proximity,
    monte_carlo_rank_uncertainty,
    pareto_dominance,
    reconstruct_openalex_abstract,
    summarize_living_stock_by_firm,
)


def test_living_and_residual_life():
    fams = pd.DataFrame({"docdb_family_id": [1, 2, 3], "priority_year": [2004, 2016, 2020]})
    apps = pd.DataFrame({"docdb_family_id": [1, 2, 2, 3], "appln_id": [10, 20, 21, 30]})
    # App 20 ceased, 21 still active -> fam 2 stays alive; app 30 ceased -> fam 3 dead; fam 1 expired (2004+20 <= 2026)
    res = compute_living_and_residual_life(fams, apps, ceased_appln_ids=[20, 30], reference_year=2026)
    assert not bool(res.loc[1, "is_alive"])
    assert res.loc[1, "residual_years"] == 0.0
    assert bool(res.loc[2, "is_alive"])
    assert res.loc[2, "residual_years"] == 10.0
    assert not bool(res.loc[3, "is_alive"])

    firm_fam = pd.DataFrame({"docdb_family_id": [1, 2, 3], "firm": ["HONDA", "UBTECH", "HONDA"]})
    summary = summarize_living_stock_by_firm(firm_fam, res, ["UBTECH", "HONDA"])
    assert summary.loc["UBTECH", "living families"] == 1
    assert summary.loc["HONDA", "living families"] == 0
    assert summary.loc["UBTECH", "Active Volume (%)"] == pytest.approx(100.0)


def test_pareto_dominance_and_monte_carlo():
    tbl = pd.DataFrame(
        {
            "Volume": [3.2, 1.4, 0.8, 1.1, 0.9],
            "Influence": [np.nan, 1.07, 1.38, 0.94, 0.53],
            "Success": [87.0, 80.0, 72.0, 63.0, 64.0],
            "Globalization": [1.5, 2.4, 2.6, 9.2, 1.1],
        },
        index=["UBTECH", "Honda", "Samsung", "Aldebaran", "Toyota"],
    )
    pf, pairs = pareto_dominance(tbl)
    # Honda strictly beats Toyota on every indicator
    assert ("Honda", "Toyota") in pairs
    assert not bool(pf.loc["Toyota", "pareto_front"])
    for leader in ["UBTECH", "Honda", "Samsung", "Aldebaran"]:
        assert bool(pf.loc[leader, "pareto_front"])

    mc = monte_carlo_rank_uncertainty(tbl, n_draws=500, top_n=4, seed=7)
    assert set(mc.index) == set(tbl.index)
    assert mc.loc["Toyota", "P(top 4) (%)"] < 15.0
    assert mc.loc["Honda", "P(top 4) (%)"] > 95.0


def test_patent_asset_index():
    firm_fam = pd.DataFrame({"docdb_family_id": [1, 2, 3], "firm": ["A", "A", "B"]})
    inf = pd.Series({1: 2.0, 2: 1.0, 3: 0.5})
    off = pd.Series({1: 4.0, 2: 2.0, 3: 1.0})  # mean = 7/3
    pai = compute_patent_asset_index(firm_fam, inf, off, ["A", "B"])
    assert pai.loc["A", "Patent Asset Index (PAI)"] > pai.loc["B", "Patent Asset Index (PAI)"]


def test_age_rescaled_pagerank():
    fams = pd.DataFrame({"docdb_family_id": [1, 2, 3, 4], "priority_year": [2015, 2015, 2018, 2018]})
    edges = pd.DataFrame({"citing": [2, 3, 4, 4], "cited": [1, 1, 1, 3]})
    pr = compute_age_rescaled_pagerank(edges, fams)
    assert pr.loc[1, "pagerank_raw"] > pr.loc[2, "pagerank_raw"]
    assert pr.loc[1, "pagerank_age_ratio"] > pr.loc[2, "pagerank_age_ratio"]
    assert pr.loc[3, "pagerank_age_ratio"] > pr.loc[4, "pagerank_age_ratio"]


def test_jaffe_cpc_proximity():
    prox = jaffe_cpc_proximity(
        ["B25J9/00", "B25J13/00", "A47L9/00"],
        {"FIRM_CLOSE": ["B25J11/00", "B25J15/00", "A47L11/00"], "FIRM_FAR": ["G06N3/00", "B62D57/032"]},
    )
    assert prox.loc["FIRM_CLOSE", "jaffe_proximity"] == pytest.approx(1.0)
    assert prox.loc["FIRM_FAR", "jaffe_proximity"] == pytest.approx(0.0)


def test_openalex_reconstruct_and_causal_science():
    txt = reconstruct_openalex_abstract({"humanoid": [0], "biped": [1], "walking": [2]})
    assert txt == "humanoid biped walking"

    patents = pd.DataFrame(
        {
            "docdb_family_id": [101, 102],
            "priority_year": [2015, 2022],
            "text": ["biped humanoid walking gait control", "humanoid dexterous robotic hand grasp"],
        }
    )
    papers = pd.DataFrame(
        {
            "openalex_id": ["W1", "W2"],
            "title": ["Biped walking control", "Dexterous hand grasping"],
            "year": [2014, 2020],
            "abstract": ["humanoid biped gait stabilization", "robotic hand grasp force"],
            "is_fundamental": [True, True],
        }
    )
    # Test causal constraint: patent 101 (2015) can ONLY see paper W1 (2014), NOT W2 (2020)
    p_embs = np.array([[1.0, 0.0], [0.0, 1.0]])
    s_embs = np.array([[0.95, 0.05], [0.05, 0.95]])
    res = compute_causal_science_proximity(patents, papers, patent_embs=p_embs, paper_embs=s_embs, top_k=1)
    assert int(res.loc[res["docdb_family_id"] == 101, "best_paper_year"].iloc[0]) == 2014
    assert int(res.loc[res["docdb_family_id"] == 102, "best_paper_year"].iloc[0]) == 2020
    assert bool(res.loc[res["docdb_family_id"] == 101, "fundamental_match"].iloc[0])
