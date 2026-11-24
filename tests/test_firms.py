"""Firm panel (src/firms.py): Thomas's method on our tables. A small made-up sector."""
import pandas as pd
import pytest

from firms import company_panel


def made_up_sector():
    rows, links = [], []
    fid = 0

    def add(applicant, years, subfield="platform", kind="firm", co=None):
        nonlocal fid
        for year in years:
            fid += 1
            rows.append((fid, year, subfield))
            names = [applicant] + ([co] if co else [])
            for name in names:
                links.append((fid, name, kind if name == applicant else "university", 1 / len(names)))

    for i, size in enumerate([30, 25, 20, 18, 15, 12]):                   # established firms, from 2005
        add(f"BIG{i}", [2005 + (k % 18) for k in range(size)])
    for i in range(6):                                                    # medium firms, 4-6 families from 2008
        add(f"MID{i}", [2008 + 3 * k for k in range(4 + i % 3)], subfield="body")
    for i, size in enumerate([9, 8, 7, 6, 5, 4]):                         # entrants, from 2016
        add(f"NEW{i}", [2016 + (k % 7) for k in range(size)])
    add("UNIV", range(2005, 2020), kind="university")                    # not a firm
    add("ONEYEAR", [2010, 2010, 2010])                                   # active in one year only
    add("LATE", [2024, 2024, 2025, 2025])                                # only truncated years
    add("SHARED", [2010, 2012, 2014, 2016], co="UNIV")                   # co-applicant: weight 1/2
    families = pd.DataFrame(rows, columns=["docdb_family_id", "priority_year", "subfield"])
    links = pd.DataFrame(links, columns=["docdb_family_id", "applicant", "applicant_type", "weight"])
    return families, links


def test_groups_and_conditions():
    families, links = made_up_sector()
    metrics, panel, eligible = company_panel(families, links)
    groups = metrics.groupby("company_group")["applicant"].apply(list).to_dict()
    assert groups["large_portfolio"] == ["BIG0", "BIG1", "BIG2", "BIG3", "BIG4"]
    assert groups["new_entrant"] == ["NEW0", "NEW1", "NEW2", "NEW3", "NEW4"]
    assert len(groups["medium_portfolio"]) == 5
    assert not set(groups["medium_portfolio"]) & set(groups["large_portfolio"])
    for name in ["UNIV", "ONEYEAR", "LATE"]:                             # not a firm / one year / truncated years only
        assert name not in set(eligible["applicant"])


def test_fractional_weight_and_panel():
    families, links = made_up_sector()
    _, _, eligible = company_panel(families, links)
    assert "SHARED" not in set(eligible["applicant"])                   # 4 shared families = 2.0 < 3: below the minimum
    _, _, eligible = company_panel(families, links, min_families=1)
    shared = eligible.set_index("applicant").loc["SHARED"]
    assert shared["total_families"] == pytest.approx(2.0)                # 4 families, each shared with a university
    metrics, panel, _ = company_panel(families, links)
    assert len(panel) == len(metrics) * (2022 - 2000 + 1)                # every firm, every complete year, zeros included
    assert panel["priority_year"].max() == 2022


def test_growth_between_windows():
    families, links = made_up_sector()
    metrics, _, _ = company_panel(families, links)
    row = metrics.set_index("applicant").loc["NEW0"]
    # NEW0: 9 families in 2016-2022, one per year (2016-2022) plus two more in 2016-2017
    assert row["families_per_year_2015_2018"] == pytest.approx((2 + 2 + 1 + 0) / 4)
    assert row["families_per_year_2019_2022"] == pytest.approx(4 / 4)
    assert row["growth_abs_per_year"] == pytest.approx(1 - 1.25)


def test_weights_must_sum_to_one():
    families, links = made_up_sector()
    links.loc[0, "weight"] = 0.5
    with pytest.raises(ValueError):
        company_panel(families, links)
