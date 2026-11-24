"""A panel of firms of the sector: five recent entrants, five medium and five large portfolios.

The method is Thomas's (group branch thomas240103-patch-1, src/applicant_analysis.py, company_panel).
Adapted to our tables:
- the families are those of the sector (rule v3), each with its priority year and its subfield
  (platform / body / control / unclear, src/subfields.py);
- the applicants are those harmonised in Step 0 (names.py), one row per family and applicant, with a
  fractional weight (the weights of a family sum to 1);
- only complete years enter the panel (first_year..last_year): the truncated years are never read as a decline;
- in Step 2 the research bodies that PATSTAT records as "COMPANY" (ATR, Kansai TLO...) are typed
  "institution" before the call, so they are not firms.
Every family is in the sector, so Thomas's condition "at least one strict family" is always true and is dropped.
"""

import pandas as pd



def company_panel(families, links, entry_year=2015, first_year=2000,
                  last_year=2022, previous=(2015, 2018), recent=(2019, 2022),
                  per_group=5, min_families=3, min_active_years=2,
                  company_types=("firm", "COMPANY")):
    """Choose five recent entrants, five medium and five large portfolios.

    families: docdb_family_id, priority_year, subfield (one row per family)
    links:    docdb_family_id, applicant, applicant_type, weight
              (one row per family and applicant)
    Returns (metrics, panel, eligible):
      metrics  one row per chosen firm: group, first year, active years,
               families, growth, stability
      panel    one row per chosen firm and year, zeros included
      eligible every firm that met the conditions, before the choice"""
    if not families["docdb_family_id"].is_unique:
        raise ValueError("families must have one row per family")
    sums = links.groupby("docdb_family_id")["weight"].sum()
    if not sums.between(0.999, 1.001).all():
        raise ValueError("the applicant weights of every family must sum to 1")

    in_window = families["priority_year"].between(first_year, last_year)
    dated = families.loc[in_window,
                         ["docdb_family_id", "priority_year", "subfield"]]
    weighted = links.merge(dated, on="docdb_family_id",
                           validate="many_to_one")
    annual = (weighted
              .groupby(["applicant", "priority_year", "subfield"])["weight"]
              .sum()
              .unstack(fill_value=0)
              .reindex(columns=["platform", "body", "control", "unclear"],
                       fill_value=0))
    annual["combined"] = annual.sum(axis=1)
    active = annual.reset_index()
    portfolios = active.groupby("applicant").agg(
        observed_start=("priority_year", "min"),
        active_years=("priority_year", "nunique"),
        total_families=("combined", "sum"),
        platform=("platform", "sum"),
        body=("body", "sum"),
        control=("control", "sum"),
        unclear=("unclear", "sum"),
    )
    is_company = links["applicant_type"].isin(company_types)
    companies = links.loc[is_company, "applicant"].unique()
    eligible = portfolios.loc[
        portfolios.index.isin(companies)
        & portfolios["active_years"].ge(min_active_years)
        & portfolios["total_families"].ge(min_families)
    ].reset_index()

    established = eligible.loc[eligible["observed_start"].lt(entry_year)]
    entrants = eligible.loc[eligible["observed_start"].ge(entry_year)]
    order = ["total_families", "applicant"]
    large = (established.sort_values(order, ascending=[False, True])
             .head(per_group))
    remaining = established.loc[
        ~established["applicant"].isin(large["applicant"])].copy()
    median_size = established["total_families"].median()
    remaining["distance_from_median"] = (
        remaining["total_families"] - median_size).abs()
    medium = (remaining.sort_values(["distance_from_median", "applicant"])
              .head(per_group))
    new = entrants.sort_values(order, ascending=[False, True]).head(per_group)
    selected = pd.concat([
        new.assign(company_group="new_entrant"),
        medium.drop(columns="distance_from_median")
              .assign(company_group="medium_portfolio"),
        large.assign(company_group="large_portfolio"),
    ], ignore_index=True)

    panel_index = pd.MultiIndex.from_product(
        [selected["applicant"], range(first_year, last_year + 1)],
        names=["applicant", "priority_year"])
    panel = (annual.groupby(level=["applicant", "priority_year"]).sum()
             .reindex(panel_index, fill_value=0).reset_index()
             .merge(selected[["applicant", "company_group", "observed_start"]],
                    on="applicant", validate="many_to_one"))
    observed = panel.loc[panel["priority_year"].ge(panel["observed_start"])]
    stability = (observed.groupby("applicant")["combined"]
                 .agg(["mean", "std", "size"]))
    metrics = selected.join(stability, on="applicant")
    metrics["active_year_share_pct"] = (
        100 * metrics["active_years"] / metrics["size"])
    metrics["annual_cv"] = metrics["std"] / metrics["mean"]
    for start, end in (previous, recent):
        in_years = panel["priority_year"].between(start, end)
        rates = panel.loc[in_years].groupby("applicant")["combined"].mean()
        metrics[f"families_per_year_{start}_{end}"] = (
            metrics["applicant"].map(rates))
    early = metrics[f"families_per_year_{previous[0]}_{previous[1]}"]
    late = metrics[f"families_per_year_{recent[0]}_{recent[1]}"]
    metrics["growth_abs_per_year"] = late - early
    metrics["growth_pct"] = 100 * (late / early.where(early.gt(0)) - 1)
    return metrics.drop(columns=["mean", "std", "size"]), panel, eligible
