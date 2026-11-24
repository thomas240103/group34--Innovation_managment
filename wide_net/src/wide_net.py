"""The wide net of the group: Thomas's robotics search, cleaned with the rules of our sector, with the sector inside it.

Thomas's search (src/thomas_retrieval.py, unchanged) returns the families that match his keywords or his robot codes
(all of B25J and B62D57 among them). Two steps make it comparable with the sector of rule v3:
1. the year of a family is its earliest priority year over its PI applications, as in Step 0 (Thomas's search
   filters each application on its own year: a family can enter through a later application);
2. the families of rule v3 that the search does not find (mostly titles in other languages without a robot code)
   are added, so that the sector is inside the net by construction. The column in_sector_v3 marks them all.
"""

import pandas as pd

FAMILY = "docdb_family_id"


def build_wide_net(net_years, sector_years, year_min=2000, year_max=2025):
    """One row per family of the wide net.

    net_years:    docdb_family_id, priority_year for the families found by Thomas's search
    sector_years: docdb_family_id, priority_year for the families of rule v3 (the Step 0 list)
    Returns docdb_family_id, priority_year, in_sector_v3, found_by_search, and a dict of counts for the notebook."""
    for name, df in (("net_years", net_years), ("sector_years", sector_years)):
        if not df[FAMILY].is_unique:
            raise ValueError(f"{name} must have one row per family")
    net = net_years.assign(found_by_search=True)
    added = sector_years.loc[~sector_years[FAMILY].isin(net[FAMILY])].assign(found_by_search=False)
    wide = pd.concat([net, added], ignore_index=True)
    wide["in_sector_v3"] = wide[FAMILY].isin(sector_years[FAMILY])
    in_window = wide["priority_year"].between(year_min, year_max)
    counts = {
        "found by the search": int(len(net)),
        "sector families not found by the search, added": int(len(added)),
        "outside the window, removed": int((~in_window).sum()),
        "sector families outside the window": int((~in_window & wide["in_sector_v3"]).sum()),
    }
    wide = wide.loc[in_window].sort_values(FAMILY, ignore_index=True)
    wide["priority_year"] = wide["priority_year"].astype(int)
    counts["wide net"] = int(len(wide))
    counts["of which in the sector (rule v3)"] = int(wide["in_sector_v3"].sum())
    return wide[[FAMILY, "priority_year", "in_sector_v3", "found_by_search"]], counts
