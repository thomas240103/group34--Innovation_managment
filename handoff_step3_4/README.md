# Handoff: Steps 3-4 (for Thomas and Leo)

Since 24 November Steps 3 and 4 are Thomas's and Leo's. This folder holds what Imma had built for them, so that it can be merged with their work (the PageRank score) instead of being redone. Steps 0-2, the Tutorial 2 notebooks and the wide net, in the main folder, are final.

| Notebook | Status | What it gives |
|---|---|---|
| `step3_present_score.ipynb` | Complete, run on PROD on 24 November | Citations of the sector (Tutorial 3: origin, categories, network, science, spillovers) and the present score of the 8 firms with at least 10 mature families (Tutorial 4), with 18 robustness variants, an OECD check and Reliance on Science. Writes `outputs/step3/present_score.csv` (the y axis of the quadrant) and `firms_for_step4.csv`. |
| `step4_future_score.ipynb` | Skeleton v0.1, runs end to end on PROD | Outcome (top 10% of 5-year citations in its year and CPC subclass), first signals, out-of-time backtest (benchmark against proposed, two models, bootstrap intervals), firm scores for 2023-2025. Every place to work on is marked `TODO(...)`. Writes `outputs/step4/future_score.csv`. |
| `step4_search_reports_check.ipynb` | Complete | The X, Y, I letters of the search reports of all offices (TLS215): 1,700 families of the sector (58%) have them, mostly from the Chinese office. |

## How to run

The notebooks read the outputs of the main folder with relative paths (`data/PROD/humanoid_robots_v2`, `ids/`, `outputs/step3`, `wide_net/outputs/wide_net`, `outputs/t2_text`). On TIP, **put them in the same folder as Steps 0-2** and run them after Step 0, Step 2, notebook 21 and the wide net. Step 3 also reads two external data sets, if they are there (see `docs/external_data.md`): the OECD Patent Quality Indicators in `~/data/OECD` and Reliance on Science in `data/ros/`.

## Step 3 in short (run of 24 November)

- **Who is scored.** 8 firms have at least 10 mature families (priority year up to 2021); 59% of the sector's families are more recent. The younger firms (the large Chinese entrants of 2023-2025 and Figure AI) are passed to Step 4 in `firms_for_step4.csv`.
- **Present score** (weighted Reciprocal Rank Fusion of Volume, Influence, Success and Globalization): a top group of four, UBTECH 87, Honda 87, Samsung 87 and Aldebaran 82, clearly above Toyota 68, Tmsuk 67 and Kawada 60. The group is the same in all 18 robustness variants; the order inside it is not.
- **Influence** is the 5-year citations of a family divided by the mean of its priority year and CPC subclass in **all of PATSTAT** (Section 4: 900 cohorts). A PageRank or other network score should be normalised the same way, or by age as in Mariani et al. (2019).
- **Network.** Section 3.2 builds the citation network between the top firms; Section 6 the knowledge spillovers by country (citations stay in the inventors' country 1.6 times more than chance).
- **Checks.** OECD Patent Quality Indicators (7% of the families) and the OECD method computed from PATSTAT for 781 families keep the same top group. Reliance on Science links 74 of the 171 families with a US grant to science.

## Step 4: where things stand

- **The training sample is the wide net** (`wide_net/`, 239,711 robotics families with the 2,907 of the sector inside), because the sector alone has about 50 highly cited families in the training years.
- **First full run** (24 November): the benchmark (classic indicators, gradient boosting) reaches AUC 0.72 on the net and beats every single signal (best: backward citations, 0.69); 31% of the families it puts in its top 10% are really valuable, three times chance. On the sector's families, AUC 0.70. The first new signals add little. Details and the list of papers: `docs/step4_literature.md`.
- **Where a PageRank score fits.** As a dynamic signal of the backtest (Section 5.4 of the skeleton: computed only on the citations that existed at the prediction moment), or as a refinement of Influence in Step 3 (Section 9). Mariani, Medo & Lafond (2019) show that PageRank must be rescaled by age to work early.
- **Open decisions** (fix them before looking at the scores): which firms Step 4 scores (Thomas's panel of 5 entrants, 5 medium and 5 large firms counted up to 2025, or the firms of Step 3 plus those waiting); how to place the young firms, which have no present score, on the quadrant.
- **One idea from Thomas's branch `codex/patent-landscape-final`:** the WIPO fields of the citing families, which can become the generality signal (Trajtenberg, Henderson & Jaffe 1997).

## What Step 5 needs

`outputs/step3/present_score.csv` (y axis) and `outputs/step4/future_score.csv` (x axis), one row per firm with the column `firm`, and the number of families of each firm for the size of the bubbles.
