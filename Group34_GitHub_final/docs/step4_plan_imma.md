> Imma's plan for Step 4 as of 23 November 2026 (exported from the group's working document). Since 24 November Steps 3-4 are Thomas's and Leo's: read it as a proposal, not a decision. The literature is summarised, with how to use each paper, in `docs/step4_literature.md`.

# Step 4 · Future score: set-up, literature and plan

2026-11-23 · Imma

This document puts everything in one place: what the professor asks, what we have, what the papers do, the algorithm we propose and how we will prove it works.

**Updated on 23 November** with the group's runs: the wide net to 2025 (the training sample), the text novelty and topics of notebook 21 on rule v3, the examiner's opinion from the search reports of all offices in PATSTAT, and the subfields platform / body / control.

## What the professor asks

- **Kickoff slide:** "it is your algorithm". Grants and citations do not exist yet for recent filings, so we score **the last 1–2 years of published applications** with forward-looking signals.
- **Possible ingredients** ("combine them, improve them or replace them"):
  - originality: 1 − Σ s² over the CPC classes of the cited patents (Trajtenberg, Henderson & Jaffe 1997);
  - generality: the same formula over the citing patents, with care on recent filings (Hall et al. 2001);
  - new recombination of CPC codes: pairs never seen before (Fleming 2001; Verhoeven, Bakker & Veugelers 2016);
  - early entry into hot subfields (course construct, tutorial of 9 November);
  - text novelty: far from the past, close to what comes after (Kelly et al. 2021; Arts, Hou & Gomez 2021).
- **"Even better: prove it works":**
  1. freeze time at T (for example 2015) and compute the score only with the data available at T;
  2. measure what happened after T: citations within 5 years, family growth, grants, later activity of the firm;
  3. compare with the baselines from the literature;
  4. beating the baselines = very high mark on the methodology, and possibly a publication.
- **Grading:** "Valuation methodology" is 20% of the mark (3 points): soundness and originality of the algorithm.
- **Course notes:** no instructions on the future score, she wants our proposals. Dedicated tutorial on **Monday 23 November, 13:00–14:30, room 4P**: she shares papers and asks for a prediction algorithm. The following lecture uses LLMs to score patents.
- **Lecture 5 slides:** cite Lai, Wei & Hwang (2026) and describe text novelty as embeddings of title and abstract compared with the 5 years before (novelty) and the 10 years after (impact).
- **Step 5:** Magic Quadrant, present score (y) against future score (x); bubbles = number of families.

## What I already have

| Material | Where | Use in Step 4 |
| --- | --- | --- |
| 2,907 families: applications, CPC, IPC, citations between families, inventors, applicants | Step 0 (TIP, `data/PROD/humanoid_robots_v2`) | the base of everything |
| Subfield of every family: platform, body or control (blind check 36/40 = 90%) | Step 0, section 7.4 (`family_subfields`) | the subfield of every comparison; hot subfields |
| English abstracts | Step 0 (TLS203 query, section 6) | text novelty, readability |
| Patent SBERT vector and BERTopic topic of 2,872 families | notebook 21 on rule v3 (`sector_embeddings_PROD_rule_v3.npy`, `family_topics_PROD_rule_v3.csv`) | text similarity, hot topics |
| Text novelty of 2,765 families, with its rank in the year | notebook 21 on rule v3, section 10 (`text_novelty_PROD_rule_v3.csv`) | a signal: it falls as the sector grows, so we use the rank |
| Examiner's opinion: X, Y or I letters in the family's own search report, all offices (TLS215): 1,700 families (58%; 84–91% of those of 2015–2022) | `step4_search_reports_check.ipynb` | a signal available once the search is done |
| The wide net: Thomas's robotics search rerun to 2025, with the sector inside it | `wide_net/wide_net_v3.ipynb` → `outputs/wide_net/wide_net_families.csv` (239,711 families, run on 23 November) | the training and test sample |
| Firms waiting for a score: Guangzhou Ligong, Shanghai Fourier, Shenzhen Zhuji Power (probably LimX Dynamics), Figure AI, Renxing, Jiangsu Yunmu, Leju, with PCT and offices | Step 3, `firms_for_step4.csv` | the firms to score |
| Panel of firms: 5 entrants, 5 medium, 5 large portfolios (Thomas) | Step 2, section 5.2 (`firm_panel.csv`) | a declared way to choose the firms, if counted to 2025 |
| Present score of the 7 mature firms | Step 3, `present_score.csv` | the y axis of the quadrant |
| Forward citations with year (all offices), X/I categories, origin | Step 3 (`forward_citation_pairs.csv`, `forward_citations_publications.csv`) | outcomes of the backtest; network for the CD and SPNP indicators |
| Legal status (refused, withdrawn, lapsed) from TLS231/TLS803 | Step 3, section 5.3 | an alternative outcome |
| Quality index with the OECD method on 781 families | Step 3, section 9.3 | an alternative outcome and a baseline |
| Growth of the CPC subfields | Step 2, section 5.3 | hot subfields |
| Text encoding (TF-IDF, MiniLM, Patent SBERT) | the professor's notebook 21 | model for the embeddings |

## Literature

### The signals (cited by the professor)

| Paper | What it says | What we take |
| --- | --- | --- |
| Fleming (2001), Management Science 47(1) | New combinations of components give inventions that are less useful on average but more variable: more failures and more breakthroughs | New CPC recombination. The outcome must be "probability of being in the top" (the tail), not the mean of citations |
| Verhoeven, Bakker & Veugelers (2016), Research Policy 45(3) | Ex-ante novelty on two dimensions: new recombination and new knowledge origins (technological and scientific), from classes and citations. The impact is strongest when the two add up | Two signals: new CPC pairs and new origins (cited classes never combined, scientific literature) |
| Kelly, Papanikolaou, Seru & Taddy (2021), AER: Insights 3(3) | Importance = a patent is different from earlier work and similar to later work; the measure predicts future citations and is linked to market value | Backward text novelty (available at once); the forward part only as an outcome in the backtest |
| Arts, Hou & Gomez (2021), Research Policy 50(2) | Novelty from text: words, bigrams, trigrams and word combinations that appear for the first time; impact = reuse by later patents; open code and data | A second text novelty, without embeddings (new words in the sector) |
| Trajtenberg, Henderson & Jaffe (1997) | Originality and generality | Originality (cited classes) |
| Funk & Owen-Smith (2017), Management Science 63(3) | CD index: a patent is "disruptive" if those who cite it do not also cite its predecessors | CD index on the citation network (open code, cdindex) |

### Lai, Wei & Hwang (2026), read in full

"Identification of valuable patents: New indicators and effects of prediction time points", Research Policy 55, 105512. Cited in the lecture 5 slides.

- **Questions:** do new indicators beat the classic ones? Can valuable patents be recognised right after grant? Does prediction improve with the patent's age? Which indicators matter most?
- **Data:** USPTO, CPC sections G and H, granted 1995–2016. "Valuable" = involved in more than two lawsuits and kept alive to the end (2,364); "not valuable" = never litigated and abandoned for non-payment of fees (2,364), matched by grant year and 4-digit CPC class.
- **27 indicators,** static (fixed at grant) or dynamic (growing with age): 14 classic ones (scope, claims, family, forward and backward citations, non-patent citations, originality, generality, technology cycle time, inventors, small entity, examination length, claim length), 4 from the examination file (US only), 3 network ones (CD, mCD, SPNP), 6 from the claim text (abstractness, readability).
- **Method:** prediction right after grant and after 2, 3 and 5 years, dynamic indicators counted only up to that date. Benchmark = classic indicators only; proposed = classic + new. Logistic regression, random forest, gradient boosting, XGBoost (best). Random 10-fold cross-validation; accuracy, precision, recall, F1.
- **Results:** accuracy 80.5% right after grant and 82.75% after 5 years (benchmark 77.3% and 79.4%), about 3 points above the benchmark at every time point. Text indicators help most early (0–2 years), network indicators later (3–5). Most important: SPNP, originality, readability, generality (from 9th to 1st with age), technology cycle time. Forward citations only 11th.
- **Their limits:** litigation is an indirect measure of value; the unit is the single patent, not the portfolio; they point to Arts et al.'s text novelty as future work.

**What we take:** the design with several time points; benchmark vs proposed at each point; new indicators computable from PATSTAT (technology cycle time, scope, time to grant, CD and SPNP, readability of the abstract); comparisons within the same year and field; XGBoost importance plus logistic signs; an outcome in their style (alive and highly cited vs withdrawn or lapsed).

**Where we do better:** validation **out of time** (train on old cohorts, test on new ones) instead of random folds; results on the real distribution, not balanced extremes (so our numbers will be lower and not directly comparable); time points from publication, since many Chinese applications are not granted yet; aggregation to the **firm**, which they leave as future work; text novelty, which they suggest and we have already computed (notebook 21).

### Other ways to predict value early

| Paper | Data and method | What we take |
| --- | --- | --- |
| Lee, Kwon, Kim & Kwon (2018), TFSC 127 | 18 input indicators defined right after grant, 3 outputs (citations), neural network; pharmaceuticals | List of indicators available at grant; input-output scheme of the backtest |
| Mariani, Medo & Lafond (2019), TFSC 146 | Important patents chosen by experts; an age-normalised PageRank recognises them before citation counts | Always compare at the same age (as in Step 3); a network baseline |
| Chung & Sohn (2020), TFSC 158 | Deep learning on text and indices, US semiconductors 2000–2015: precision and recall above 75% on top patents | Text alone carries information: a text baseline |
| Aristodemou (Cambridge) | Neural networks predicting OECD indicators (quality_index_4, generality, citations, renewals) at 4, 8 and 12 years; out-of-time, out-of-sample and k-fold tests | The OECD index as an outcome (we have it from 9.3); the out-of-time test |

### The examiner's opinion: search reports

| Paper | What it says | What we take |
| --- | --- | --- |
| [Czarnitzki, Hussinger & Leten (2011)](https://www.zew.de/PU68857-1), ZEW Discussion Paper 11-021 | At the EPO a patent can be cited as background or because it threatens the novelty of a later application (a "blocking" citation). Blocking citations track the value of the cited patent more closely than other forward citations: one standard deviation more of them goes with a market value about 10% higher | The X and Y letters carry information on value: the blocking patents of Step 3 (forward), and our extension backwards, the letters found against the family itself |
| [Lemley & Sampat (2012)](https://law.stanford.edu/wp-content/uploads/2015/06/rest_a_00194.pdf), Review of Economics and Statistics 94(3) | Examiners differ: more experienced USPTO examiners cite less prior art and grant more, so the outcome depends on who examines | The letters depend on who examines: we compare within the year, with the office as a control (92% of our reports are Chinese) |

### Framing and text similarity

- **Rotolo, Hicks & Martin (2015), Research Policy 44(10):** emerging technologies have five attributes: radical novelty, relatively fast growth, coherence, prominent impact, uncertainty and ambiguity. Our signals map onto them: novelty → text novelty and recombination; growth → hot subfields; impact → the backtest outcome; uncertainty → Fleming's variance.
- **Hain, Jurowetzki, Buchmann & Wolf (2022), TFSC 177:** text embeddings and nearest neighbours for patent similarity, with open code. It is the procedure of notebook 21 (Patent SBERT + cosine).

### External check: LexisNexis IP (2026)

An industry analysis of humanoid robotics (a vendor, not peer reviewed): more than 26,000 families defined with their own classifiers; China has 73% of the active families on morphology and 63% of portfolio strength, the US 5% of the families but 11% of the strength. Their top 10 dedicated start-ups: Fourier, AgiBot, LimX Dynamics, Pudu, Unitree, Figure AI, Agile Robots, Apptronik, Leju, Agility. UBTECH is the only dedicated humanoid company in their overall top 10. **Four of our firms waiting for Step 4 are in their top 10** (Fourier, Shenzhen Zhuji/LimX, Figure AI, Leju), and UBTECH is in our top group: we are scoring the right firms.

## Proposed algorithm (to be discussed)

**Unit.** The family first, then the firm (mean or share of its recent families). Lai et al. stop at the single patent and leave the portfolio as future work: the firm level is our extension.

**Signals available at publication** (none needs citations received):

| Signal | How | Source | Type |
| --- | --- | --- | --- |
| Text novelty | 1 − mean similarity with the 10 most similar families of the previous 5 years (Patent SBERT on the abstract). Computed in notebook 21 for 2,765 families: the median falls from 0.08–0.10 (2005–2008) to 0.05–0.06 (2021–2025) because the sector grows, so we use the rank within the year. Second version: new words (Arts et al.) | Kelly et al. 2021; Arts et al. 2021; notebook 21 | static |
| Examiner's opinion | the family's own search report holds an X, Y or I document (any office, TLS215): 1,700 families covered (58%; 84–91% of 2015–2022, 60% of 2024, 44% of 2025). No report yet = missing, never zero; compared within the year, with the office of the report as a control | Czarnitzki et al. 2011; Lemley & Sampat 2012 | static, once the search is done |
| New recombination | share of the family's CPC group pairs never seen before in PATSTAT (a self-join on TLS224 limited to the sector's groups, to test on TIP) | Fleming 2001; Verhoeven et al. 2016 | static |
| Originality | spread of the classes of the cited families (backward citations, available with the search report); 2nd most important in Lai et al. | Trajtenberg et al. 1997 | static |
| Early entry into hot subfields | the family enters a subfield that was growing faster than the sector before filing (momentum up to T), early in its curve. Three readings agree on which grow: CPC groups (Step 2, section 5.3), title subfields (Step 0, section 7.4) and text topics (notebook 21, section 9): feet shrink; legs, gait planning and balance control grow | course construct | static |
| Early economic signals | PCT application, offices within 12 months of priority, number of inventors, links to science (non-patent citations), collaboration with universities | literature on patent value | static |
| From Lai et al. | technology cycle time (median age of cited families); scope (number of 4-digit CPC); time to grant (instead of examination data, US only); readability (SMOG) of the abstract, since PATSTAT has no claim text | Lai et al. 2026 | static |
| Network indicators | CD index and SPNP on the citation network | Funk & Owen-Smith 2017; Lai et al. 2026 | dynamic |
| Firm level | growth of filings in the sector, share of families with PCT, variety of subfields | — | — |

**Static and dynamic (Lai et al.).** Each indicator is marked static (fixed at publication) or dynamic (grows with age: family size, citations received, generality, CD, SPNP). At each prediction time point, dynamic indicators are counted only up to that date.

**Combination: two versions to compare.**

1. **Fixed rules,** as for the present score (weighted RRF).
2. **A model trained on the past:** logistic regression, random forest and XGBoost, as Lai et al. Outcome: "is the family in the top 10% of 5-year citations of its year and subfield?". We report indicator importance and the signs of the logistic regression.

**Application.** The families of 2023–2025 (the last years published) of the quadrant's firms. The firm's score is the x axis of the quadrant.

## Proof that it works: the backtest

**Training sample ≠ sector (decided on 17 November).** The sector and the sample on which we train and test the model are two different things.

- The **sector** describes the market and scores the firms: it must be precise, so it stays the 2,907 families of Step 0 (92.5% precision).
- The **training and test sample** of the model can be much larger: the wide net, Thomas's robotics search (19 keywords, all of B25J and B62D57; 176,342 families to 2022), rerun to 2025 with the 2,907 families of the sector inside it (folder wide_net, run on 23 November: 239,711 families, 2,907 of them in the sector; 59,373 in 2010–2017, against about 480 in the sector). The model learns which signals come before a highly cited patent, always comparing each family with families of the same year and subfield.
- We report two results: performance on the whole training sample and performance on the sector's families only. If the model also works on the sector, we can apply it to the humanoid firms with good reason, and the method is shown to hold for robotics in general, not only for our sample.

Why not widen the sector instead: the draft rule v0.2 (8,268 families) would give only about 2.8 times more families, and about 4 in 10 of them are not humanoid robots (grippers, quadrupeds, toys). More data shrinks the intervals but does not remove a systematic error: the model would learn what makes gripper or quadruped patents cited, and Steps 1–3 would describe partly another sector.

1. **Freeze time.** T = 2012–2017, in rolling windows: for each T the signals use only data up to T. The families come from the wide net above, not from the sector alone.
2. **Outcomes after T.**
  - main: the family is in the top 10% of 5-year citations of its year and subfield (complete up to T = 2017);
  - alternatives: offices added later, grant, the OECD-method quality index of Step 3 (9.3);
  - in Lai's style: family alive and highly cited vs application withdrawn or lapsed (TLS231/TLS803).
3. **Time points (Lai et al.).** At publication and after 2, 3 and 5 years; we report how much is lost by predicting early.
4. **Benchmark vs proposed** at each time point: classic indicators alone vs classic indicators + our signals.
5. **Baselines:** a large family at T, number of claims, originality alone, text novelty alone, recombination alone, the firm's volume.
6. **Metrics:** AUC and precision in the top 10%; accuracy, precision, recall and F1 of the "valuable" class (as Lai); bootstrap intervals for all; always on the real, unbalanced distribution. Then at firm level: rank of the score at T against the later present score.
7. **Out-of-time validation.** Train on earlier T, test on later T, never on the same years. Lai et al. use random folds; for a score about the future, testing on later years is the fair test (as in Aristodemou).

**Risks to state.**

- The sector alone is small (about 1,000 families in 2010–2017, so about 100 in the top 10%), which is why we train on the larger robotics sample; the results on the sector's families only will still have wide intervals, and we report them as they are.
- Our numbers will not be comparable with Lai's 80%: they classify balanced extremes (litigated vs abandoned), we score every family.
- The examiner's opinion is in practice the Chinese office's (1,569 of the 1,700 families): offices give the letters differently, so the office is a control. Before using it we check that it works: on the families of 2015–2017, those without X or Y should be cited more in the next five years.
- Text novelty falls by construction as the sector grows (notebook 21): we use the rank within the year, and we check it against later citations, because its correlation with forward similarity (Spearman −0.93) is expected by construction and proves nothing.

## Open decisions and next steps

**To decide.**

- **Young firms on the y axis.** They have no present score: compute it with the indicators available, or place them at the bottom as "not measurable" and state it.
- **Known players outside the sector** (Agility, Apptronik, 1X, Unitree, AgiBot have few or no families): a firm-level extension on all their robotics families, validated by Imma on a sample read by hand.
- **Which firms Step 4 scores.** Reuse Thomas's panel (5 entrants, 5 medium, 5 large portfolios, Step 2, section 5.2) counted to 2025, so that it includes the 2023–2025 wave, with the rule fixed before looking at any score.
- [x] **The common Step 0** (2,907 families vs 8,268)
- **Optional:** Reliance on Science (`pcs_oa_uspto.csv`, 1.4 GB, US patents only) for links to science; LLM scoring with the professor's OpenAI key, only through an environment variable, never in a file or in git.
- [x] Rerun Leo's notebook 21 on the final sector (group decision, pull request #2).

**Proposed order of work.**

1. Step 4 notebook, section 1: data and firms (from the Step 0 tables and the Step 3 files).
2. The signals, one section each, each marked static or dynamic and tested alone in the backtest.
3. Combination, comparison with the baselines and with the benchmark at each time point.
4. Firm scores and the file for Step 5.
5. After 23 November: update with the professor's material.

## Sources

- [Lai, Wei & Hwang (2026), Research Policy](https://www.sciencedirect.com/science/article/abs/pii/S0048733326001034)
- [Fleming (2001), Management Science](https://funginstitute.berkeley.edu/wp-content/uploads/2012/10/Recombinant-Uncertainty-in-Technological-Search.pdf)
- [Verhoeven, Bakker & Veugelers (2016), Research Policy](https://www.skema.edu/en/faculty-and-research/publications/measuring-technological-novelty-patent-based-indicators)
- [Kelly et al. (2021), working paper](https://dimitris-papanikolaou.github.io/website/assets/papers/MeasuringInnovationLR_AERI.pdf) · [NBER](https://www.nber.org/papers/w25266)
- [Arts, Hou & Gomez (2021), Research Policy](https://lirias.kuleuven.be/retrieve/595840)
- [Lee et al. (2018), TFSC](https://econpapers.repec.org/RePEc:eee:tefoso:v:127:y:2018:i:c:p:291-303)
- [Mariani, Medo & Lafond (2019), TFSC](https://econpapers.repec.org/RePEc:eee:tefoso:v:146:y:2019:i:c:p:644-654)
- [Aristodemou, Identifying Valuable Patents](https://www.repository.cam.ac.uk/items/3b66d468-3706-44a7-9f30-ad0bee24d59a)
- [Rotolo, Hicks & Martin (2015)](https://sro.sussex.ac.uk/id/eprint/56071/1/2015RP_Rotolo_Hicks_Martin_Preprint.pdf)
- [LexisNexis IP, Patent data in humanoid robotics](https://lexisnexisip.com/resources/patent-data-in-humanoid-robotics)
- [Czarnitzki, Hussinger & Leten (2011), ZEW Discussion Paper 11-021](https://www.zew.de/PU68857-1)
- [Lemley & Sampat (2012), Review of Economics and Statistics](https://law.stanford.edu/wp-content/uploads/2015/06/rest_a_00194.pdf)

The PDF of Lai et al. was downloaded with PoliTo access: it stays off GitHub.

