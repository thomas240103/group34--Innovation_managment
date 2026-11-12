# group34--Innovation_managment

## Tutorial 2: patent text for the humanoid robot sector

These files apply the teacher's Tutorial 2 to our sector. Both notebooks ran on PROD on TIP, and each result is explained in a text cell under the code that produced it.

| File | What it does |
|---|---|
| `t2_20_epab_humanoid.ipynb` | Writes our sector rule as a query on EPAB, the EPO full-text database. It checks where the humanoid words appear (title, abstract, claims), links EPAB to PATSTAT, describes the claims and compares the examiners' search reports with robotics in general. |
| `t2_21_text_humanoid.ipynb` | Turns the patent abstracts into vectors with several methods (TF-IDF, MiniLM, Patent SBERT) and checks which one groups the patents best. It tests whether text similarity finds humanoid patents our keywords miss, finds the topics of the sector and how they grow (BERTopic), and measures how new each patent is. |
| `config/sector_rule.yaml` | Our Step 0 rule, written once: the CPC codes, the keywords, the exclusions, the years and the segments. Both notebooks read it, so they study exactly the same patents. To change the rule, we edit this file only. |
| `src/sector_rule.py` | Reads the rule file, checks it, and turns it into the PATSTAT queries that find the sector's patents. |
| `tests/test_sector_rule.py` | Tests the rule code on a small made-up database, so a change to the rule code cannot silently change the sector. Run with `pytest tests`. |
| `.gitignore` | Keeps the `outputs/` folder out of git. It holds PATSTAT data, which is licensed and must not be shared. |

To run a notebook, open it on TIP from this folder: it needs `config/` and `src/` next to it, and it writes its files to `outputs/`.
