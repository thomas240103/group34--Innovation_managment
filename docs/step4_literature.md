# Steps 3-4 · Literature: the papers and how we can use them

Imma, 24 November 2026. For Thomas and Leo, who take over Steps 3-4.

This file lists the papers we collected for the present and future scores. For each paper it says, in one line, what the paper shows, and then how we can use it in our project. In this repository, Imma's plan for Step 4 is in `docs/step4_plan_imma.md`. The PDFs are in the group's Drive folder: the links are below and in `docs/external_data.md`.

## 1. Scoring patents on the citation network (the PageRank idea)

| Paper | What it shows | How we can use it |
|---|---|---|
| Mariani, Medo & Lafond (2019), "Early identification of important patents: design and validation of citation network metrics", *Technological Forecasting and Social Change* 146 | On patents chosen as important by experts, PageRank on the citation network recognises them earlier than citation counts, **but only once the score is rescaled by age**: raw PageRank favours old patents, which had more time to collect citations. Their rescaled PageRank compares each patent with patents of the same age. | **This is the closest paper to the PageRank idea.** (1) Rescale by age: compare each family's PageRank with the families of the same priority year, as Step 3 does for Influence (cohort of priority year and CPC subclass, Hall et al. 2001). (2) Test it the way they do: is it better than the plain citation count at telling which families later become highly cited? A backtest that freezes time in the past and checks later citations answers this, with PageRank as one more signal. |
| Lai, Wei & Hwang (2026), "Identification of valuable patents: new indicators and effects of prediction time points", *Research Policy* 55, 105512 | 27 indicators on US patents. **SPNP** (search path node pair, a measure of how many citation paths pass through a patent) is their most important indicator. Network indicators help most 3-5 years after grant, text indicators in the first 2 years. | SPNP is the alternative to PageRank in the same family of measures: try both. Because network measures grow with the age of the patent, they are **dynamic** signals: at each prediction moment, count only the citations that existed by then. |
| Funk & Owen-Smith (2017), "A dynamic network measure of technological change", *Management Science* 63(3) | CD index: a patent is disruptive if the patents that cite it do not also cite its predecessors, consolidating if they do. Open code (Python package `cdindex`). | A third network measure, next to PageRank and SPNP. Same rule: dynamic, so counted only up to the prediction moment. |
| Hall, Jaffe & Trajtenberg (2001), NBER Working Paper 8498 (the NBER patent citation data file) | Citation counts must be compared within the same year and technology class, because older patents and some fields collect more citations. | Already used in Step 3 for Influence (benchmark from all of PATSTAT, 900 cohorts). Any network score should be normalised the same way. |

**A practical note for PageRank on our data.** The network of Step 3 is between DOCDB families (table TLS228). For the sector alone it is small: 2,750 citations between families of the sector (Step 2, Section 5.2). PageRank becomes more stable on the wide net (239,711 robotics families, `wide_net/`), where the sector's families can receive weight from all of robotics. In both cases, a family can only be cited after it is published, so recent families will always score low: this is exactly the age bias that Mariani et al. correct.

## 2. Signals known when a patent is published (the future score)

| Paper | What it shows | How we can use it |
|---|---|---|
| Trajtenberg, Henderson & Jaffe (1997), "University versus corporate patents: a window on the basicness of invention", *Economics of Innovation and New Technology* 5(1) | **Originality**: 1 − Σ s² over the classes of the cited patents. **Generality**: the same over the citing patents. | Originality is known at publication. Generality needs citations received, so it is dynamic. Thomas's branch `codex/patent-landscape-final` counts the WIPO fields of the citing families: it can become the generality signal. |
| Fleming (2001), "Recombinant uncertainty in technological search", *Management Science* 47(1) | New combinations of components give inventions that are less useful on average but more variable: more failures and more breakthroughs. | Signal: the share of the family's pairs of CPC groups never seen together before. The outcome should be "is the family in the top 10%", not the mean of citations. |
| Verhoeven, Bakker & Veugelers (2016), "Measuring technological novelty with patent-based indicators", *Research Policy* 45(3) | Novelty in two parts: new recombination of classes, and new origins of knowledge (technological and scientific). Impact is highest when they add up. | Two signals: new CPC pairs, and citations to fields or to science never combined before. |
| Kelly, Papanikolaou, Seru & Taddy (2021), "Measuring technological innovation over the long run", *American Economic Review: Insights* 3(3) | A patent is important if its text is different from earlier patents and similar to later ones; the measure predicts citations and market value. | Text novelty of 2,765 families is already computed (notebook 21, Section 10). Use its rank within the year: the raw value falls as the sector grows. |
| Arts, Hou & Gomez (2021), "Natural language processing to identify the creation and impact of new technologies in patent text", *Research Policy* 50(2) | Novelty from new words and word combinations appearing for the first time; impact from their reuse. Open code and data. | A second text novelty without embeddings. Lai et al. name it as future work. |
| Czarnitzki, Hussinger & Leten (2011), ZEW Discussion Paper 11-021 | At the EPO, a "blocking" citation (one that threatens the novelty of a later application) tracks the value of the cited patent better than other citations. | The X, Y and I letters of the search reports: in Step 3 forward (blocking patents), and in Step 4 backward, as the examiner's opinion of the family itself (1,700 families, 58% of the sector, `handoff_step3_4/step4_search_reports_check.ipynb`). |
| Lemley & Sampat (2012), "Examiner characteristics and patent office outcomes", *Review of Economics and Statistics* 94(3) | Examiners differ: the outcome depends on who examines. | Compare the letters within the year and with the office as a control (92% of our reports are Chinese). |
| Harhoff, Scherer & Vopel (2003), "Citations, family size, opposition and the value of patent rights", *Research Policy* 32(8) | Family size, citations and oppositions are linked to the value of patents. | Classic indicators of the benchmark. Family size grows with age: only offices reached within 12 months are known at publication. |
| Lee, Kwon, Kim & Kwon (2018), *Technological Forecasting and Social Change* 127 | 18 indicators known at grant predict later citations (neural network, pharmaceuticals). | A list of indicators available early; the input-output scheme of the backtest. |
| Chung & Sohn (2020), *Technological Forecasting and Social Change* 158 | Deep learning on text and indices finds the top US semiconductor patents with precision and recall above 75%. | Text alone carries information: a text baseline. |

## 3. Proving that a score works

| Source | What it shows | How we can use it |
|---|---|---|
| Lai, Wei & Hwang (2026) | Benchmark (classic indicators) against proposed (classic + new), at publication and after 2, 3 and 5 years. XGBoost best; about 3 points of accuracy above the benchmark. | A design to reuse, with two improvements: test **out of time** (train on old cohorts, test on later ones; they use random folds), and on the real, unbalanced distribution (they compare litigated with abandoned patents, so their 80% is not comparable). |
| Aristodemou, "Identifying valuable patents" (University of Cambridge) | Neural networks predicting the OECD indicators at 4, 8 and 12 years, with out-of-time tests. | The OECD quality index as an alternative outcome; the out-of-time test. |
| Squicciarini, Dernis & Criscuolo (2013), "Measuring patent quality: indicators of technological and economic value", OECD STI Working Paper 2013/03 | The OECD Patent Quality Indicators: definitions and composite index. | Step 3, Section 9.3 computes the index with the OECD method from PATSTAT for 781 families: an outcome or a check for any new score. |

**A practical point.** The classic indicators alone (backward citations, inventors, scope, citations to science) already predict later citations well. A network score like PageRank should be tested against them, not against zero.

## 4. Framing and data

| Source | How we can use it |
|---|---|
| Rotolo, Hicks & Martin (2015), "What is an emerging technology?", *Research Policy* 44(10) | Five attributes of an emerging technology (radical novelty, fast growth, coherence, prominent impact, uncertainty): a frame for the deck. |
| Hain, Jurowetzki, Buchmann & Wolf (2022), *Technological Forecasting and Social Change* 177 | Text embeddings and nearest neighbours for patent similarity: the method of notebook 21. |
| Marx & Fuegi, *Reliance on Science* (relianceonscience.org) | Links from US patents to scientific articles; used in Step 3, Section 3.5 (74 of 171 families with a US grant). |
| LexisNexis IP (2026), "Patent data in humanoid robotics" | An industry check (not peer reviewed): four of the firms waiting for a future score are in their top 10 of dedicated start-ups. |

## Links

- Lai, Wei & Hwang (2026): https://www.sciencedirect.com/science/article/abs/pii/S0048733326001034
- Mariani, Medo & Lafond (2019): https://econpapers.repec.org/RePEc:eee:tefoso:v:146:y:2019:i:c:p:644-654
- Fleming (2001): https://funginstitute.berkeley.edu/wp-content/uploads/2012/10/Recombinant-Uncertainty-in-Technological-Search.pdf
- Verhoeven, Bakker & Veugelers (2016): https://www.skema.edu/en/faculty-and-research/publications/measuring-technological-novelty-patent-based-indicators
- Kelly et al. (2021): https://dimitris-papanikolaou.github.io/website/assets/papers/MeasuringInnovationLR_AERI.pdf (NBER: https://www.nber.org/papers/w25266)
- Arts, Hou & Gomez (2021): https://lirias.kuleuven.be/retrieve/595840
- Lee et al. (2018): https://econpapers.repec.org/RePEc:eee:tefoso:v:127:y:2018:i:c:p:291-303
- Aristodemou: https://www.repository.cam.ac.uk/items/3b66d468-3706-44a7-9f30-ad0bee24d59a
- Czarnitzki, Hussinger & Leten (2011): https://www.zew.de/PU68857-1
- Lemley & Sampat (2012): https://law.stanford.edu/wp-content/uploads/2015/06/rest_a_00194.pdf
- Rotolo, Hicks & Martin (2015): https://sro.sussex.ac.uk/id/eprint/56071/1/2015RP_Rotolo_Hicks_Martin_Preprint.pdf
- LexisNexis IP: https://lexisnexisip.com/resources/patent-data-in-humanoid-robotics

The PDFs are not in this repository (copyright): they are in the group's Drive folder (`docs/external_data.md`).
