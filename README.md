# Group 34 · Humanoid robots: a patent landscape for Electrolux

Innovation Management, Politecnico di Torino, 2026/27. Sector: humanoid robots. Client: Electrolux.

**The question.** Electrolux wants to know how the humanoid-robot sector is doing, which segments are growing, and which emerging players are worth buying or partnering with. We answer with patent data from PATSTAT, on the EPO TIP platform.

**Status (28 November 2026).** Steps 0-4 have been revised after an internal review (below). **Every notebook must be rerun on PROD** (*Restart and Run All*, in the order of "How to run") before any number is used: the readings marked "⚠ Rerun needed" or "To write after the PROD run" are not up to date. Step 5 (quadrant) and Step 6 (recommendation) are still to be written; their input is `outputs/step4/magic_quadrant_data.csv`.

### Review of 28 November 2026: what changed

| Problem | Fix | Where |
|---|---|---|
| The Magic Quadrant could not be built: the present score existed only for 7 old firms, the future score only for recent filers | One **common set of firms** scored on both axes: a present score *as of today* (depreciated living stock, citations to date normalised by age and office, success, age-adjusted globalization) and a future score that is 0 for a firm with no recent family | Step 3 §11, Step 4 §6-7, `src/quadrant.py` |
| The present score rewarded lapsed portfolios | Volume = **Active Volume** (living families); the course Volume is a robustness variant | Step 3 §7-8 |
| The title rule misses Boston Dynamics, 1X, AgiBot... | Their robotics families since 2015 join the common set (**extension**), checked by a blind reading (threshold 80%), flagged until read | Step 3 §11, `config/sector.yaml` |
| Step 4 features leaked later information | **Point-in-time** features: applications filed within 12 months, citations and X/Y/I of publications within 18 months | Step 4 §2-3 |
| Target mixed office habits | Top-10% cohort = year × subclass × **office of first filing** | Step 4 §2 |
| Model chosen on the years it reported; overlapping CIs read as a gain; mechanical secondary target; t0+2y in the headline | Validation 2014-15 chooses, test 2016-17 reports; **paired bootstrap** of the gain; secondary target dropped; t0+2y is a diagnostic | Step 4 §4 |
| Uncalibrated probabilities summed into firm scores; tiny firms on top | **Isotonic calibration** with an honest check, **distribution-shift** diagnostics (PSI, adversarial AUC), **shrinkage** towards the sector mean | Step 4 §6 |
| No firm-level validation | **Firm-level backtest** frozen at 2016 vs. size and PCT baselines | Step 4 §6.3 |
| 2023-2025 (56% of the sector) only shaded grey | **Nowcast** of the incomplete years from publication delays | Step 1 §7.3, `src/nowcast.py` |
| Nothing about Electrolux's market | **Application domains** (home, care, industry, commerce, education) with a blind check; **appliance makers** benchmark | Step 2 §5.3c, Step 3 §2.5, `src/domains.py` |
| One labeller | **Second blind reader** on the independent sample, Cohen's kappa | Step 0 §5.24, `src/agreement.py` |
| Readings with numbers the run did not produce (Reliance on Science, OECD) | Flagged "not reproduced when the file is missing"; aggregates saved | Step 3 §3.5, §9.2 |
| Science proximity cosine did not separate firms | Within-year z-score and rank only | Step 3 §3.6 |
| Notebook 20 mixed rule v0.2 and v3 numbers | Banner and conclusions say which numbers belong to which rule | `t2_20_epab_humanoid.ipynb` |
| Kick-off layout | `config/sector.yaml` (shared choices), `src/01_extract.py` ... `05_future_score.py` (run the notebooks) | `config/`, `src/` |

**Readings to do by hand** (sheets are written to `outputs/`, git-ignored): the extension (`outputs/step3/16_reading_sheet_extension.csv`), the second reader of Step 0 (`outputs/step0/prod/17_reading_sheet_second_reader.csv`), the application domains (`outputs/step2/18_reading_sheet_domains.csv`). Each has its threshold fixed in the notebook before reading.

## Contents

| Folder or file | What it holds |
|---|---|
| `step0_sector_definition.ipynb` | **Step 0.** The sector rule, its validation on families read by hand, and the tables the other steps read |
| `step1_volume_growth.ipynb` | **Step 1.** Size, growth, technologies, geography, who files |
| `step2_concentration_subfields.ipynb` | **Step 2.** Concentration, leaders and entrants, growing subfields, PEST for Electrolux |
| `t2_20_epab_humanoid.ipynb`, `t2_21_text_humanoid.ipynb` | **Tutorial 2** (Leo): EP full text and search reports; patent text, topics and novelty |
| `wide_net/` | Thomas's robotics search to 2025 (239,711 families) with the sector inside: the training sample for Step 4 |
| `handoff_step3_4/` | Imma's Step 3 (present score) and the check of the search reports for Step 4, with a README for Thomas and Leo |
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
2. Run the notebooks with `ENV = "PROD"` in this order: Step 0 → Step 1 → Step 2 → notebooks 20 and 21 → `wide_net/wide_net_v3.ipynb` → Step 3 → Step 4 (Step 4 reads `outputs/step3/present_score_quadrant.csv` and `quadrant_families.csv`, written by Step 3 Section 11). Or run `python src/run_pipeline.py` (or one step, e.g. `python src/04_present_score.py`). Step 4 keeps its query caches in one folder per universe (`outputs/step4/cache/universe_<hash>/`), so a changed universe never reuses old queries.
3. Each notebook writes to `outputs/`, which git ignores.

## Data and licence

PATSTAT data are licensed and stay on TIP: no data file, no reading sheet with titles or abstracts, and no API key enters git. The OECD Patent Quality Indicators, Reliance on Science and the papers are shared in the group's Drive folder (`docs/external_data.md`).

## Who did what

The frame (sector rule v3, its validation, Steps 0-2, the Step 3 draft) is Imma's. **Thomas:** the wide net, the subfield patterns, the panel of firms, the alias table. **Leo:** the Tutorial 2 notebooks on patent text, the code structure (config, src, tests). **Mostafa:** an independent rerun of rule v3 on PATSTAT that finds the same 1,281 families of 2000-2022 (a check of reproducibility). Steps 3-4 are now Thomas's and Leo's. Details in `docs/methods_and_results.md`.
