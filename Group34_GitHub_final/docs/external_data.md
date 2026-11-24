# External data and papers (not in this repository)

Some inputs cannot go on GitHub: the files are too large (GitHub refuses files over 100 MB), their licence does not allow redistribution, or they are copyrighted papers. The group shares them in a Drive folder:

**Drive folder:** _link to be added by Imma_ (`Group34_shared_data_and_papers.zip`)

| What | In the Drive folder | Official source | Used by |
|---|---|---|---|
| OECD Patent Quality Indicators, August 2026 (EPO and USPTO, 492 MB; built on PATSTAT Spring 2026) | `OECD_Patent_Quality_Indicators/` (two `.7z` files and the OECD guide) | The OECD guide with the download link of every file: https://webfs-sti.oecd.org/files/STI-PIE/IP_DATA/2026_2/OECD%20Patent%20Databases%20-%20August%202026.pdf (files `202608_OECD_PATENT_QUALITY_EPO.7z` and `202608_OECD_PATENT_QUALITY_USPTO.7z`). Free for research; access is requested through the OECD STI Micro-data Lab (oe.cd/ipstats). Cite as "OECD Patent Quality Indicators database, August 2026". | Step 3, Section 9.3 (check of the present score); a possible outcome for Step 4 |
| Reliance on Science, release of July 2026 (`pcs_oa_uspto.csv.gz`, 241 MB) | `Reliance_on_Science/` | Marx and Fuegi, relianceonscience.org, licence CC BY-NC 4.0 | Step 3, Section 3.5 (links from US patents to science) |
| Lai, Wei & Hwang (2026), *Research Policy* 55, 105512 | `papers/` | https://www.sciencedirect.com/science/article/abs/pii/S0048733326001034 (PoliTo access) | Step 4: the design of the backtest |
| Course papers and reports (KITe WP 71, WIPO landscapes and working paper, Clarivate Global Innovators 2017, inventive concentration, AI patents example) | `papers/course/` | Course material | Steps 1-3 (concentration measures, landscape structure) |
| Lecture slides on patent valuation and knowledge spillovers | `slides/` | Course material | Steps 3-4 |
| Imma's Step 4 plan as PDF | `docs/` | Same content as `docs/step4_plan_imma.md` | Steps 3-4 |

## Where to put them on TIP

- **OECD:** extract the two `.7z` files (`pip install py7zr`, then `py7zr x <file>.7z`) into `~/data/OECD`. Step 3 looks there; without the files it skips that one check.
- **Reliance on Science:** copy `pcs_oa_uspto.csv.gz` into `data/ros/` next to the notebooks (Step 3 also looks in `~/data/ros`). A browser upload of a large file can stop halfway: check the size (241 MB) or the md5 (`a6460aed4bb0f00a1c2a8564b5d5667d`) after the upload, or upload it in parts.
- Like PATSTAT data, these files never enter git: `.gitignore` excludes `*.7z`, `*.gz`, `*.csv` and the `data/` folder.

The other papers of the literature are listed with their links in `docs/step4_literature.md`; most of them are open (working-paper versions).
