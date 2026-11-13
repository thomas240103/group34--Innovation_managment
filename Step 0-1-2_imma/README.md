# Group 34 · Humanoid robots: a patent landscape for Electrolux

Innovation Management, Politecnico di Torino, 2026. Sector: humanoid robots. Client: Electrolux.

This repository holds the code of our patent landscape. The analysis runs on PATSTAT, on the EPO TIP platform. Each notebook explains every result in a text cell under the code that produced it.

The numbers below come from the run of 13 November 2026 on PATSTAT PROD. TIP reloads its data from time to time, so a later run can give slightly different numbers.

## Contents

| File | What it does |
|---|---|
| `step0_sector_definition.ipynb` | **Step 0.** Defines the humanoid sector, measures its precision on samples read by hand, compares the rule with text methods (BM25, Patent SBERT), builds the applicant names and saves the tables the next steps read. |
| `step1_volume_growth.ipynb` | **Step 1.** Size and growth of the sector against all patents and robotics; technology mix; geography; who files (firms, universities). |
| `step2_concentration_subfields.ipynb` | **Step 2.** Concentration of applicants (CR4, CR8, HH, Gini, Lorenz curve, Lotka), leaders and entrants, the subfields that grow, and a PEST analysis for Electrolux. |
| `config/sector_rule_v3.yaml` | The accepted sector rule: terms, codes, exclusions, window. |
| `src/sector_rule.py` | The rule as functions: from a table of families to the column `in_sector_v3`. |
| `src/names.py` | Harmonisation of applicant names (brand key, aliases) and the pairwise precision, recall and F1 against the gold standard. |
| `src/measures.py` | Concentration measures (CR, HH, CV, Gini, Lorenz, Lotka) and the Wilson interval. |
| `tests/` | Tests of `src/` on small made-up cases, and a test that `src/` and `config/` say exactly what the notebooks say. Run with `python -m pytest tests`. |
| `labels/step0_labels.csv` | Our hand labels: reading, sample ID, family ID, strict and broad label. No titles or abstracts. |
| `requirements.txt`, `.gitignore` | Packages to install; files that never enter git (see "Data and licence"). |

The notebooks contain their code in full, so each one can be read and run on its own. `src/` holds a copy of the code that the steps share, and the tests keep the copy and the notebooks identical: if one is changed without the other, the tests fail.

The notebooks run in this order: Step 0, then Step 1, then Step 2. Step 0 saves the tables that Steps 1 and 2 read.

## The sector (Step 0)

**Unit and window.** One DOCDB family is one invention and counts once. Its year is the earliest priority year. We keep patents of invention (PI) with a priority year from 2000 to 2025. 2022 is the last complete year: later years are still being published.

**Rule.** A family is in the sector when its title names a humanoid robot: a humanoid term (humanoid, biped, android, anthropomorphic, human-like and their Chinese, Japanese or Korean compounds) followed by "robot", with at most one word in between, and no exclusion. The exclusions are:
- exoskeletons and prostheses;
- crash-test dummies and mannequins;
- virtual characters without a robot;
- a humanoid term that only describes a part ("humanoid wrist", "anthropomorphic hand").

**Result.** 2,907 families.

**Precision.** 37 of 40 families (92.5%) are humanoid robots, with a 95% Wilson interval of 80.1% to 97.4%. The 40 families come from a new random sample. One reader labelled them blind, against a definition written before reading.

**Every attempt is declared.** Each rule was fixed before its sample was read, and it was accepted only if it reached the threshold fixed in advance:

| Attempt | Families | Strict precision | Decision |
|---|---|---|---|
| Blocks A–D (strong word in title or abstract, robot codes, walking codes, face codes) | — | 62.2% | rejected |
| Block A (strong word in the title) | 3,572 | 88.8% (71/80) | rejected (below 90%) |
| Block A tightened (exclusions for parts) | 3,298 | 87.5% (35/40) | rejected |
| **Version 3 (the term names the robot)** | **2,907** | **92.5% (37/40)** | **accepted** |
| Recovery block R (first sentence of the abstract) | 452 | 67.5% (27/40) | rejected |
| Extension block W ("biped" anywhere, two words before "robot") | 228 | 40.0% (16/40) | rejected |

**Checks of the rule.**
- **Precision by period.** On the 141 families we read inside the sector (40 of them from the independent sample), precision is lowest in 2000–2009 (13/16) and between 93% and 99% afterwards. By office it is 96% for families filed only in China, so the Chinese share of the sector is not inflated by errors.
- **Recall.** The sector misses about 30% of the humanoid families of the wider net. It misses more in 2000–2009 (54% of the humanoids we read in that period are outside the sector, against 22–28% later), so early growth is overstated. Step 1 shows this with a sensitivity check.
- **Text methods.** On 391 labelled families, the rule separates humanoids from the rest better than the text methods (AUC 0.841, against 0.752 for Patent SBERT and 0.659 for BM25). We use the text methods as a check, not to define the sector.

**Why the sector is smaller than in the earlier versions:** see the next section.

**Applicant names.** Each applicant gets the best name available: the harmonised name (HAN) first, then PSN, then the standardised name, then the printed name. Names are then grouped by a brand key, which:
- removes legal forms and Chinese place names;
- keeps the full name for universities, institutes and individuals;
- applies a few certain aliases (YOUBIXUAN = UBTECH, YUSHU = UNITREE, ALDEBARAN = SOFTBANK).

We measure the brand key on the course's gold standard (3,192 names of 481 organisations). On the half of the organisations that we did not use for any choice, it reaches F1 0.936 (precision 0.992).

We also tested the course's Terrorizer method: its weights were chosen on the other half and then measured on this one. It reaches F1 0.846 with a wide grid and 0.466 with a narrow one. On our sector it merges different Chinese firms that share a city name, so we keep the brand key.

## Why the sector has 2,907 families, and not 5,000 or 8,000

Earlier versions of the sector were larger:
- the group's first Step 0 (October) had 5,033 families, with a precision of about 79% in our October reading;
- the group's draft rule v0.2, used in the Tutorial 2 notebooks of the branch `tutorial2`, has 8,268 families on PROD (7,522 one day earlier, before a TIP data update), and its precision was never measured.

We made the sector smaller on purpose. Every result of Steps 1 to 4 (growth, countries, leaders, concentration, scores) is computed on these families. If many of them are not humanoid robots, every result describes something else: grippers, walking machines, toys. This section shows, step by step, where the families went and why.

**From the wide net to the sector.** Each row was decided by reading a random sample blind, with the rule and the acceptance threshold fixed before reading. One family is one invention and counts once. Only patents of invention (PI) count, as in the professor's template.

| Step | Families | Strict precision (sample) | Decision |
|---|---|---|---|
| Wide net: humanoid and robot keywords, IPC and CPC codes (PI and utility models) | 42,351 | — | candidates only, deliberately wide |
| Blocks A–D after the exclusions, PI and utility models | 7,796 | — | utility models kept only as a sensitivity check |
| **Blocks A–D, PI only.** This is close to the structure of the draft rule v0.2: a humanoid word in the title or the abstract, or a robot code with a medium word | **5,808** | **62.2%** (95% CI 56.2–67.5) | rejected: below 90% |
| &nbsp;&nbsp;of which A: a humanoid word in the title, with a robot | 3,572 | 92.5% (37/40) | kept |
| &nbsp;&nbsp;of which B: the humanoid word only in the abstract, with a robot code | 993 | 20.0% (6/30) | removed |
| &nbsp;&nbsp;of which C: walking-robot code or words, with human leg parts | 1,116 | 6.7% (2/30) | removed |
| &nbsp;&nbsp;of which D: face-robot code, with human face parts | 127 | 26.7% (4/15) | removed |
| Block A, second sample (title and abstract read) | 3,572 | 88.8% (71/80, both samples) | below 90%: tightened |
| Block A tightened (humanoid only as the adjective of a part, e.g. "humanoid wrist", removed) | 3,298 | 87.5% (35/40) | rejected |
| **Version 3: the humanoid term must name the robot** ("humanoid robot", "biped walking robot") | **2,907** | **92.5% (37/40, 95% CI 80.1–97.4)** | **accepted** |
| Recovery block R (the first sentence of the abstract names a humanoid robot) | +452 | 67.5% (27/40) | rejected |
| Extension block W ("biped" anywhere, two words before "robot") | +228 | 40.0% (16/40) | rejected |

**What each cut removed.**
1. **Blocks B, C and D** added 2,236 families, but from their samples only about 300 of them (about 14%) are humanoid robots, or parts and methods designed for one: this is the strict label that defines the sector (Step 0, Section 5). Most of the others are close to humanoids but outside the definition:
   - in B the humanoid is cited as one possible use of a robot part (strict 20%, broad 93%);
   - C is mostly walking machines whose legs are not those of a humanoid (strict 6.7%, broad 63%);
   - in D the face mechanisms are related to humanoids but not designed for one (strict 27%, broad 100%).

   The Tutorial 2 notebooks, run on the draft rule that includes this kind of family, show the same:
   - "hands and fingers" is 30% of that sector, many probably ordinary grippers;
   - about 3% are toys, massage devices and robotic animals;
   - 40% of the EP publications that enter through a humanoid word do not claim a humanoid;
   - of those that enter through a robot code and a medium word, only 3% do.
2. **From block A to version 3** we removed 665 families: titles where "humanoid" describes a part ("humanoid dexterous hand"), is used in another sense ("humanoid intelligent control"), or does not name the robot. Among the 120 block A families we had already read, version 3 removed 19: 10 were not humanoid robots and 9 were. So this cut also costs some true humanoids: version 3 keeps 91.5% of the humanoids we had read. On a new sample, its precision is 92.5%.
3. **R and W**, the two attempts to win back families, did not reach 90% on their own new samples, so they stay out.

**What the smaller sector costs, and what it buys.**
- **It costs recall.** The sector misses about 30% of the humanoid families of the wide net, more of them in 2000–2009. Its counts are a lower bound, and Step 1 shows the effect on growth with a sensitivity check. Some known players (Boston Dynamics, Tesla, Unitree, 1X, Hyundai) are missing, most likely because their patents do not name a humanoid robot in the title; we check this before Step 3.
- **It buys results that are about humanoid robots.** With the 5,808 families of blocks A–D, about 2,200 families (4 in 10) would not be humanoid robots. With version 3, about 9 in 10 are. The intervals are wide, because each sample has 40 families, but every rule was tested on families that had not been used to build it.

**Families and patents.** The 2,907 families hold 3,714 applications (patents of invention), about 1.3 per family. We count families, not applications: an invention filed in China, the US and Europe is one invention, not three.

## Main results

**Step 1: size and growth**
- **Growth from 2012 to 2022** (compound annual): the sector grows 9.1% a year (9.2% after correcting for the precision of each period), robotics (IPC B25J) 15.4%, all patents 5.9%. The sector is flat from 2017 to 2022.
- **Share of robotics:** 4.9 per 1,000 robotics families in 2022, 25 in 2024 and 56 in 2025. 2023–2025 are incomplete years, but sector and robotics are incomplete in the same way, so the share is less biased than the counts.
- **Technology:**
  - B25J (manipulators) 47.6% of the classes;
  - B62D (legged locomotion) 22.4%;
  - mechanical engineering 72.7% of the WIPO fields;
  - computing or AI classes only 8.4% of the families of 2017–2022.
- **Geography:** China 65%, Japan 16%, Korea 10%. Only 12.6% of the families are filed at two or more offices.
- **Who files:** universities hold 47.3% of the families of 2017–2022 (fractional counting).

**Step 2: who leads**
- **Low concentration:** 724 applicants; CR4 12.5%; HH 0.008, which is equivalent to 133 applicants of equal size; Gini 0.50. Among firms only (240) it is higher: CR4 27.3%, HH 0.027 (37 firms of equal size).
- **Consolidation:** on three-year windows, CR4 rises from 15% (2012) to 30% (2022).
- **Leaders:** of the 15 largest applicants, 12 are Chinese; the other three are Figure AI, Honda and Aldebaran/SoftBank. Nine are recent entrants, six of them from 2023–2025.
- **Known players missing.** Boston Dynamics, Tesla, Unitree, Hyundai, 1X and Electrolux have no or almost no family in the sector. This is a limit of a title-based rule, stated in the report.
- **Subfields:** legged locomotion and robot navigation codes grow faster than the sector.

## Checks before a result is used

1. Every notebook runs from top to bottom with **Restart & Run All**, in the order Step 0 → Step 1 → Step 2.
2. Every number written in a text cell is checked against the output above it after the final run.
3. The date of the run that produced the numbers is written at the top of this README. A count that changes between two runs is first checked against a TIP data update (the sector had 2,907 families in every run so far).
4. Every rule is fixed before the sample that measures it is read, and every attempt stays in the table above, accepted or not.
5. Planned: a second reader labels the 40 families of the independent sample blind, to measure agreement between readers.

## Data and licence

PATSTAT data are licensed and stay on TIP. Git does not hold:
- any data file (csv, parquet, gz, pickle) or the `outputs/` and `data/` folders;
- reading sheets, which contain titles and abstracts: `labels/` keeps only family IDs and labels;
- API keys. If a notebook calls an external service, the key is read from an environment variable and never written in a file.

## How to run

1. Open the TIP Jupyter environment and clone this repository.
2. Install the packages: `pip install -r requirements.txt`, then check the shared code with `python -m pytest tests`.
3. Run the notebooks in the order above with `ENV = "PROD"`. With `ENV = "TEST"` the code runs, but the numbers mean nothing.
4. Each notebook writes its files to `outputs/`, which git ignores.

## Limits

- **Recall:** the rule is precise but misses about 30% of the humanoid families, more of them before 2010.
- **One reader:** all hand labels come from one reader so far.
- **Missing players:** patents that describe a humanoid without naming it in the title are missed. This is why some well-known players are absent.
- **Applicant country** is known for only 16.6% of the families. We estimate it from the office of first filing.
- **The last three years are incomplete.** We use them only as shares, never as counts.
