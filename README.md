# Group 34 · Humanoid robots: a patent landscape for Electrolux

Innovation Management, Politecnico di Torino, 2026/27. Sector: humanoid robots. Client: Electrolux.

**The question.** Electrolux wants to know how the humanoid-robot sector is doing, which segments are growing, and which emerging players are worth buying or partnering with. We answer with patent data from PATSTAT, on the EPO TIP platform.

**Status (24 November 2026).** Steps 0-2 are final. Steps 3-4 are Thomas's and Leo's: Imma's drafts are in `handoff_step3_4/`, to be merged with their work.

## Contents

| Folder or file | What it holds |
|---|---|
| `step0_sector_definition.ipynb` | **Step 0.** The sector rule, its validation on families read by hand, and the tables the other steps read |
| `step1_volume_growth.ipynb` | **Step 1.** Size, growth, technologies, geography, who files |
| `step2_concentration_subfields.ipynb` | **Step 2.** Concentration, leaders and entrants, growing subfields, PEST for Electrolux |
| `t2_20_epab_humanoid.ipynb`, `t2_21_text_humanoid.ipynb` | **Tutorial 2** (Leo): EP full text and search reports; patent text, topics and novelty |
| `wide_net/` | Thomas's robotics search to 2025 (239,711 families) with the sector inside: the training sample for Step 4 |
| `handoff_step3_4/` | Imma's Step 3 (present score), the Step 4 skeleton and the check of the search reports, with a README for Thomas and Leo |
| `docs/` | `methods_and_results.md` (all details), `step4_literature.md` (papers and how to use them), `step4_plan_imma.md`, `external_data.md` |
| `config/`, `src/`, `tests/` | The sector rule, the code shared by the notebooks, and its tests |
| `labels/`, `ids/` | Our hand labels and the list of the 2,907 families (IDs only, no texts) |

## The sector in one paragraph

A family is in the sector when its title names a humanoid robot (a humanoid term followed by "robot", in English, Chinese, Japanese or Korean), with exoskeletons, dummies, virtual characters and humanoid-shaped parts excluded. Patents of invention, earliest priority year 2000-2025 (2023-2025 still incomplete). **2,907 families. Precision 92.5% (37 of 40, 95% CI 80.1-97.4%)** on a new random sample read blind; recall about 70%. Every rule tried, accepted or not, is in `docs/methods_and_results.md`.

## Main results

- **Growth (Step 1).** 9.1% a year from 2012 to 2022, against 15.4% for robotics and 5.9% for all patents; then a jump in 2023-2025. China 65% of the families, Japan 16%, Korea 10%; universities hold 47% of the families of 2017-2022.
- **Competition (Step 2).** Fragmented (720 applicants, top four 12.6%) but consolidating (top four from 15% to 30% of the families between 2012 and 2022). Of the 15 largest applicants, 12 are Chinese; nine are recent entrants. Control methods grow fastest (from 39% to 53% of the families).
- **Present value (Step 3, draft).** Top group UBTECH, Honda, Samsung and Aldebaran, the same in all 18 robustness variants; the young firms of 2023-2025 are left to Step 4.

## How to run

1. On TIP, clone the repository and install the packages: `pip install -r requirements.txt`. Check the shared code with `python -m pytest tests`.
2. Run the notebooks with `ENV = "PROD"` in this order: Step 0 → Step 1 → Step 2 → notebooks 20 and 21 → `wide_net/wide_net_v3.ipynb` → the notebooks of `handoff_step3_4/` (from the same folder).
3. Each notebook writes to `outputs/`, which git ignores.

## Data and licence

PATSTAT data are licensed and stay on TIP: no data file, no reading sheet with titles or abstracts, and no API key enters git. The OECD Patent Quality Indicators, Reliance on Science and the papers are shared in the group's Drive folder (`docs/external_data.md`).

## Who did what

The frame (sector rule v3, its validation, Steps 0-2, the Step 3 and Step 4 drafts) is Imma's. **Thomas:** the wide net, the subfield patterns, the panel of firms, the alias table. **Leo:** the Tutorial 2 notebooks on patent text, the code structure (config, src, tests). **Mostafa:** an independent rerun of rule v3 on PATSTAT that finds the same 1,281 families of 2000-2022 (a check of reproducibility). Steps 3-4 are now Thomas's and Leo's. Details in `docs/methods_and_results.md`.
