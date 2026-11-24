"""The wide net (wide_net/src/wide_net.py): the sector ends up inside the net, with the same window. Made-up families."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "wide_net" / "src"))
from wide_net import build_wide_net  # noqa: E402


def test_the_sector_is_inside_the_net():
    net = pd.DataFrame({"docdb_family_id": [1, 2, 3, 4, 5], "priority_year": [1998, 2005, 2015, 2024, 2026]})
    sector = pd.DataFrame({"docdb_family_id": [2, 3, 6, 7], "priority_year": [2005, 2015, 2023, 2012]})
    wide, counts = build_wide_net(net, sector)
    assert set(wide["docdb_family_id"]) == {2, 3, 4, 6, 7}                # 1998 and 2026 are outside 2000-2025
    assert set(wide.loc[wide["in_sector_v3"], "docdb_family_id"]) == {2, 3, 6, 7}
    assert set(wide.loc[~wide["found_by_search"], "docdb_family_id"]) == {6, 7}
    assert counts["sector families not found by the search, added"] == 2
    assert counts["outside the window, removed"] == 2
    assert counts["of which in the sector (rule v3)"] == 4


def test_one_row_per_family_is_required():
    net = pd.DataFrame({"docdb_family_id": [1, 1], "priority_year": [2005, 2006]})
    with pytest.raises(ValueError):
        build_wide_net(net, pd.DataFrame({"docdb_family_id": [2], "priority_year": [2005]}))
