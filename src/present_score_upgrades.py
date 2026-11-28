"""Step 3 SOTA upgrades: economic living-patent stock, OpenAlex implicit science linkage,
Pareto dominance, Monte Carlo rank uncertainty, Patent Asset Index, age-rescaled PageRank,
and Jaffe technological proximity to Electrolux.

Designed to be imported by step3_present_score.ipynb and unit-tested independently.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import networkx as nx
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Part A: Living Patents & Residual-Life-Weighted Depreciated Patent Stock
# ---------------------------------------------------------------------------
CEASED_PATTERN = r"CEASE|LAPSE|EXPIR|DISCONTINU|WITHDRAW|REFUS|REJECT|ABANDON|REVOK"
TRANSFER_PATTERN = r"TRANSFER|ASSIGN|CHANGE OF OWNER|CHANGE OF APPLICANT|MERGER|INSOLV|BANKRUPT"


def compute_living_and_residual_life(
    families: pd.DataFrame,
    national_apps: pd.DataFrame,
    ceased_appln_ids: Iterable[int],
    reference_year: int = 2026,
    statutory_term: int = 20,
) -> pd.DataFrame:
    """Flag whether each family is still in force and compute its residual life (years).

    A family is considered alive if:
      1. Its earliest priority year is within the statutory term (`priority_year + statutory_term > reference_year`), AND
      2. At least one of its national applications has NOT had a cease/lapse/discontinuation legal event
         (or if it has no national applications recorded yet, it stays alive within the statutory term).

    Returns a DataFrame indexed by `docdb_family_id` with columns:
      `priority_year`, `within_term`, `has_active_app`, `is_alive`, `residual_years`, `residual_weight`.
    """
    ceased = set(int(x) for x in ceased_appln_ids)
    fam = families[["docdb_family_id", "priority_year"]].drop_duplicates("docdb_family_id").copy()
    fam["priority_year"] = fam["priority_year"].astype(int)

    if len(national_apps):
        apps = national_apps[["docdb_family_id", "appln_id"]].drop_duplicates().copy()
        apps["app_alive"] = ~apps["appln_id"].astype(int).isin(ceased)
        fam_app_alive = apps.groupby("docdb_family_id")["app_alive"].any()
        fam["has_active_app"] = fam["docdb_family_id"].map(fam_app_alive).fillna(True).astype(bool)
    else:
        fam["has_active_app"] = True

    remaining_raw = (fam["priority_year"] + statutory_term - reference_year).clip(lower=0, upper=statutory_term)
    fam["within_term"] = remaining_raw > 0
    fam["is_alive"] = fam["within_term"] & fam["has_active_app"]
    fam["residual_years"] = np.where(fam["is_alive"], remaining_raw, 0).astype(float)
    fam["residual_weight"] = fam["residual_years"] / float(statutory_term)
    return fam.set_index("docdb_family_id")


def summarize_living_stock_by_firm(
    firm_fam: pd.DataFrame,
    living_df: pd.DataFrame,
    selected_firms: Sequence[str],
) -> pd.DataFrame:
    """Aggregate total families, living families, active share, mean residual years, and depreciated stock."""
    merged = firm_fam[["docdb_family_id", "firm"]].drop_duplicates().join(living_df, on="docdb_family_id")
    sector_alive = max(int(living_df["is_alive"].sum()), 1)
    sector_res_stock = max(float(living_df["residual_weight"].sum()), 1e-9)

    g = merged.groupby("firm")
    out = pd.DataFrame(
        {
            "total families": g["docdb_family_id"].nunique(),
            "living families": g["is_alive"].sum(),
            "alive share (%)": g["is_alive"].mean() * 100.0,
            "Active Volume (%)": g["is_alive"].sum() / sector_alive * 100.0,
            "mean residual years (all)": g["residual_years"].mean(),
            "residual-weighted stock": g["residual_weight"].sum(),
            "Residual Stock Share (%)": g["residual_weight"].sum() / sector_res_stock * 100.0,
        }
    ).reindex(selected_firms)
    return out


# ---------------------------------------------------------------------------
# Part B: OpenAlex Fast-Rising Papers + Causal BM25/Dense RRF Science Linkage
# ---------------------------------------------------------------------------
def reconstruct_openalex_abstract(inverted_index: Optional[dict]) -> str:
    """Reconstruct plain text from OpenAlex's `abstract_inverted_index`."""
    if not inverted_index or not isinstance(inverted_index, dict):
        return ""
    pos_to_word: Dict[int, str] = {}
    for word, positions in inverted_index.items():
        for pos in positions:
            pos_to_word[int(pos)] = str(word)
    if not pos_to_word:
        return ""
    return " ".join(pos_to_word[i] for i in sorted(pos_to_word))


def fetch_openalex_humanoid_papers(
    cache_path: Path,
    year_min: int = 2000,
    year_max: int = 2025,
    max_papers: int = 600,
    mailto: str = "group34@polito.it",
) -> pd.DataFrame:
    """Fetch top cited humanoid-robotics papers from OpenAlex (free CC0 API) and cache locally."""
    cache_path = Path(cache_path)
    if cache_path.exists():
        return pd.read_csv(cache_path)

    rows = []
    per_page = 200
    n_pages = max(1, (max_papers + per_page - 1) // per_page)
    base_url = "https://api.openalex.org/works"

    for page in range(1, n_pages + 1):
        params = urllib.parse.urlencode(
            {
                "search": '"humanoid robot" OR "biped robot" OR "bipedal locomotion"',
                "filter": f"publication_year:{year_min}-{year_max},has_abstract:true,type:article|preprint",
                "sort": "cited_by_count:desc",
                "per-page": per_page,
                "page": page,
                "mailto": mailto,
            }
        )
        req = urllib.request.Request(f"{base_url}?{params}", headers={"User-Agent": f"Group34-PoliTo ({mailto})"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = data.get("results", [])
        if not results:
            break
        for w in results:
            abs_txt = reconstruct_openalex_abstract(w.get("abstract_inverted_index"))
            if not abs_txt:
                continue
            pub_year = int(w.get("publication_year") or 0)
            cby = w.get("counts_by_year") or []
            recent_3y = sum(int(x.get("cited_by_count", 0)) for x in cby if int(x.get("year", 0)) >= year_max - 2)
            rows.append(
                {
                    "openalex_id": w.get("id", ""),
                    "title": (w.get("display_name") or "").strip(),
                    "year": pub_year,
                    "cited_by_count": int(w.get("cited_by_count") or 0),
                    "recent_3y_cites": recent_3y,
                    "abstract": abs_txt,
                }
            )
        if len(rows) >= max_papers:
            break

    df = pd.DataFrame(rows).drop_duplicates("openalex_id").head(max_papers).reset_index(drop=True)
    if len(df):
        # Flag "becoming fundamental" papers: top 25% recent citation velocity within publication era
        df["era"] = pd.cut(df["year"], bins=[1999, 2009, 2016, 2021, 2026], labels=["2000-09", "2010-16", "2017-21", "2022-25"])
        q75 = df.groupby("era", observed=False)["recent_3y_cites"].transform(lambda s: s.quantile(0.75))
        df["is_fundamental"] = (df["recent_3y_cites"] >= q75) & (df["recent_3y_cites"] > 0)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache_path, index=False)
    return df


def compute_causal_science_proximity(
    patent_df: pd.DataFrame,
    paper_df: pd.DataFrame,
    patent_embs: Optional[np.ndarray] = None,
    paper_embs: Optional[np.ndarray] = None,
    top_k: int = 5,
    rrf_k: int = 60,
) -> pd.DataFrame:
    """Compute strictly causal (`paper_year <= patent_priority_year`) implicit closeness to science.

    Combines BM25 lexical matching and (when provided) dense cosine similarity via RRF,
    returning for each patent family:
      - `science_cosine_top5`: mean dense cosine similarity to top-k prior papers (or NaN if no embeddings)
      - `science_bm25_top5`: mean BM25 score to top-k prior papers
      - `science_rrf_score`: fused RRF closeness score to prior papers
      - `fundamental_match`: whether any of the top-k RRF-matched prior papers is flagged `is_fundamental`
      - `best_paper_year`, `science_lag_years`
    """
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        class BM25Okapi:  # lightweight pure-Python BM25Okapi fallback when rank_bm25 is not installed
            def __init__(self, corpus, k1: float = 1.5, b: float = 0.75):
                self.k1, self.b = k1, b
                self.doc_len = np.array([len(d) for d in corpus], dtype=float)
                self.avgdl = float(self.doc_len.mean()) if len(corpus) else 1.0
                self.tfs = [Counter(d) for d in corpus]
                df: Dict[str, int] = Counter()
                for tf in self.tfs:
                    for term in tf:
                        df[term] += 1
                n = len(corpus)
                self.idf = {t: float(np.log((n - c + 0.5) / (c + 0.5) + 1.0)) for t, c in df.items()}

            def get_scores(self, query):
                scores = np.zeros(len(self.tfs), dtype=float)
                for q in query:
                    idf = self.idf.get(q)
                    if idf is None:
                        continue
                    for i, tf in enumerate(self.tfs):
                        f = tf.get(q, 0)
                        if f:
                            dl = self.doc_len[i]
                            scores[i] += idf * (f * (self.k1 + 1.0)) / (f + self.k1 * (1.0 - self.b + self.b * dl / self.avgdl))
                return scores

    tok = lambda s: re.findall(r"[a-z0-9]{2,}", str(s).lower())
    paper_years = paper_df["year"].to_numpy(dtype=int)
    paper_fund = paper_df.get("is_fundamental", pd.Series(False, index=paper_df.index)).to_numpy(dtype=bool)
    paper_tokens = [tok(f"{t} {a}") for t, a in zip(paper_df["title"], paper_df["abstract"])]
    bm25 = BM25Okapi(paper_tokens)

    use_dense = patent_embs is not None and paper_embs is not None and len(patent_embs) == len(patent_df)
    if use_dense:
        p_norm = patent_embs / np.clip(np.linalg.norm(patent_embs, axis=1, keepdims=True), 1e-12, None)
        s_norm = paper_embs / np.clip(np.linalg.norm(paper_embs, axis=1, keepdims=True), 1e-12, None)
        cos_mat = p_norm @ s_norm.T
    else:
        cos_mat = None

    out_rows = []
    for idx, row in enumerate(patent_df.itertuples(index=False)):
        py = int(row.priority_year)
        valid_mask = paper_years <= py
        valid_idx = np.flatnonzero(valid_mask)
        if len(valid_idx) == 0:
            out_rows.append(
                {
                    "docdb_family_id": int(row.docdb_family_id),
                    "priority_year": py,
                    "science_cosine_top5": np.nan,
                    "science_bm25_top5": np.nan,
                    "science_rrf_score": np.nan,
                    "fundamental_match": False,
                    "best_paper_year": np.nan,
                    "science_lag_years": np.nan,
                }
            )
            continue

        q_tokens = tok(getattr(row, "text", getattr(row, "abstract", "")))
        bm25_scores = bm25.get_scores(q_tokens)[valid_idx]
        bm25_order = np.argsort(-bm25_scores)
        bm25_ranks = np.empty(len(valid_idx), dtype=float)
        bm25_ranks[bm25_order] = np.arange(1, len(valid_idx) + 1)

        if use_dense:
            cos_scores = cos_mat[idx, valid_idx]
            cos_order = np.argsort(-cos_scores)
            cos_ranks = np.empty(len(valid_idx), dtype=float)
            cos_ranks[cos_order] = np.arange(1, len(valid_idx) + 1)
            rrf_scores = (1.0 / (rrf_k + bm25_ranks)) + (1.0 / (rrf_k + cos_ranks))
        else:
            cos_scores = None
            rrf_scores = 1.0 / (rrf_k + bm25_ranks)

        k_eff = min(top_k, len(valid_idx))
        # Ties of the fused rank are broken by the dense cosine (then the BM25 score), never by the order of the
        # papers in the table: with few papers, BM25 can give them identical scores and the RRF then ties exactly.
        tie_break = cos_scores if use_dense else bm25_scores
        top_local = np.lexsort((-bm25_scores, -tie_break, -rrf_scores))[:k_eff]
        top_global = valid_idx[top_local]

        best_year = int(paper_years[top_global[0]])
        out_rows.append(
            {
                "docdb_family_id": int(row.docdb_family_id),
                "priority_year": py,
                "science_cosine_top5": float(np.mean(cos_scores[top_local])) if use_dense else np.nan,
                "science_bm25_top5": float(np.mean(bm25_scores[top_local])),
                "science_rrf_score": float(np.mean(rrf_scores[top_local])),
                "fundamental_match": bool(paper_fund[top_global].any()),
                "best_paper_year": best_year,
                "science_lag_years": float(py - best_year),
            }
        )

    res = pd.DataFrame(out_rows)
    # Within-year percentile rank of science closeness (removes cohort drift, mirrors Kelly et al. rank)
    res["science_rank_in_year"] = res.groupby("priority_year")["science_rrf_score"].rank(pct=True)
    return res


# ---------------------------------------------------------------------------
# Part C1: Pareto Dominance & Monte Carlo Uncertainty (Saisana et al. 2005)
# ---------------------------------------------------------------------------
def pareto_dominance(table: pd.DataFrame) -> Tuple[pd.DataFrame, List[Tuple[str, str]]]:
    """Identify Pareto-undominated firms and exact dominance pairs (higher = better on all cols).

    Missing values are compared conservatively: firm A dominates firm B only if A is >= B on
    every indicator where both are observed (and has no missing indicator where B is observed),
    and strictly > B on at least one indicator.
    """
    firms = list(table.index)
    vals = table.astype(float)
    dominated_by: Dict[str, List[str]] = {f: [] for f in firms}
    pairs: List[Tuple[str, str]] = []

    for a in firms:
        va = vals.loc[a]
        for b in firms:
            if a == b:
                continue
            vb = vals.loc[b]
            # A cannot dominate B if A is missing an indicator that B has
            if (va.isna() & vb.notna()).any():
                continue
            both = va.notna() & vb.notna()
            if not both.any():
                continue
            if (va[both] >= vb[both]).all() and (va[both] > vb[both]).any():
                dominated_by[b].append(a)
                pairs.append((a, b))

    summary = pd.DataFrame(
        {
            "pareto_front": [len(dominated_by[f]) == 0 for f in firms],
            "n_dominators": [len(dominated_by[f]) for f in firms],
            "dominated_by": [", ".join(dominated_by[f]) for f in firms],
        },
        index=firms,
    )
    return summary, pairs


def monte_carlo_rank_uncertainty(
    indicator_table: pd.DataFrame,
    firm_family_metrics: Optional[pd.DataFrame] = None,
    n_draws: int = 5000,
    top_n: int = 4,
    method: str = "rrf",
    alpha: float = 1.0,
    seed: int = 42,
) -> pd.DataFrame:
    """Joint Monte Carlo uncertainty over random Dirichlet weights and (optional) family bootstrap.

    Parameters
    ----------
    indicator_table : DataFrame (firms x indicators), higher = better.
    firm_family_metrics : optional DataFrame with columns ['firm', 'Volume', 'Influence', 'Success', 'Globalization']
        at the family level for bootstrap sampling error; if None, varies weights only (Dirichlet).
    """
    rng = np.random.default_rng(seed)
    firms = list(indicator_table.index)
    cols = list(indicator_table.columns)
    n_firms, n_cols = len(firms), len(cols)
    base_vals = indicator_table.astype(float).to_numpy()
    rrf_c = float(n_firms)

    # Pre-group family-level arrays if bootstrap table is provided
    fam_groups = None
    if firm_family_metrics is not None and len(firm_family_metrics):
        fam_groups = {}
        for f in firms:
            sub = firm_family_metrics[firm_family_metrics["firm"] == f]
            fam_groups[f] = {c: sub[c].dropna().to_numpy(dtype=float) for c in cols if c in sub.columns}

    weights_mat = rng.dirichlet(np.full(n_cols, alpha), size=n_draws)
    ranks_out = np.empty((n_draws, n_firms), dtype=float)

    for d in range(n_draws):
        mat = base_vals.copy()
        if fam_groups is not None:
            for fi, f in enumerate(firms):
                for ci, c in enumerate(cols):
                    arr = fam_groups[f].get(c)
                    if arr is not None and len(arr) >= 5 and np.isfinite(base_vals[fi, ci]):
                        idx_b = rng.integers(0, len(arr), size=len(arr))
                        if c == "Volume":
                            # Poisson/bootstrap perturbation around family count share
                            mat[fi, ci] = base_vals[fi, ci] * (rng.poisson(len(arr)) / max(len(arr), 1))
                        else:
                            mat[fi, ci] = float(np.mean(arr[idx_b]))

        # Compute column-wise scores
        if method == "rrf":
            col_scores = np.full_like(mat, np.nan)
            for ci in range(n_cols):
                v = mat[:, ci]
                ok = np.isfinite(v)
                if ok.any():
                    s = pd.Series(v[ok]).rank(ascending=False, method="min").to_numpy()
                    col_scores[ok, ci] = (rrf_c + 1.0) / (rrf_c + s)
        else:
            means = np.nanmean(mat, axis=0)
            col_scores = mat / np.where(means > 0, means, np.nan)

        w = weights_mat[d]
        valid = np.isfinite(col_scores)
        w_eff = np.where(valid, w[None, :], 0.0)
        w_sum = w_eff.sum(axis=1, keepdims=True)
        w_norm = np.divide(w_eff, w_sum, out=np.zeros_like(w_eff), where=w_sum > 0)
        scores = np.nansum(np.where(valid, col_scores * w_norm, 0.0), axis=1)
        # Higher score -> rank 1
        order = np.argsort(-scores, kind="mergesort")
        r = np.empty(n_firms, dtype=float)
        r[order] = np.arange(1, n_firms + 1)
        ranks_out[d] = r

    return pd.DataFrame(
        {
            "median_rank": np.median(ranks_out, axis=0),
            "mean_rank": np.mean(ranks_out, axis=0),
            "rank_p05": np.percentile(ranks_out, 5, axis=0),
            "rank_p95": np.percentile(ranks_out, 95, axis=0),
            f"P(top {top_n}) (%)": (ranks_out <= top_n).mean(axis=0) * 100.0,
            "P(rank 1) (%)": (ranks_out == 1).mean(axis=0) * 100.0,
        },
        index=firms,
    ).sort_values(["mean_rank", "median_rank"])


# ---------------------------------------------------------------------------
# Part C2: Patent Asset Index (Ernst & Omland 2011) & Age-Rescaled PageRank
# ---------------------------------------------------------------------------
def compute_patent_asset_index(
    firm_fam: pd.DataFrame,
    family_influence_noself: pd.Series,
    family_offices: pd.Series,
    selected_firms: Sequence[str],
    living_mask: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """Compute Patent Asset Index (Ernst & Omland 2011): sum over families of Tech Relevance x Market Coverage.

    - Technology Relevance (TR) = cohort-normalized 5-year non-self forward citations (mean = 1.0).
    - Market Coverage (MC) = number of distinct offices / sector mean offices (normalized so avg = 1.0).
    - Competitive Impact (CI) = TR * MC.
    - Patent Asset Index (PAI) = sum(CI) across a firm's families (optionally restricted to living families).
    """
    df = firm_fam[["docdb_family_id", "firm"]].drop_duplicates().copy()
    df["TR"] = df["docdb_family_id"].map(family_influence_noself)
    avg_off = max(float(family_offices.mean()), 1e-9)
    df["MC"] = df["docdb_family_id"].map(family_offices) / avg_off
    if living_mask is not None:
        df["alive"] = df["docdb_family_id"].map(living_mask).fillna(True).astype(bool)
    else:
        df["alive"] = True

    valid = df.dropna(subset=["TR", "MC"]).copy()
    valid["CI"] = valid["TR"] * valid["MC"]
    valid["CI_alive"] = np.where(valid["alive"], valid["CI"], 0.0)

    g = valid.groupby("firm")
    out = pd.DataFrame(
        {
            "families scored (PAI)": g["docdb_family_id"].nunique(),
            "mean Tech Relevance": g["TR"].mean(),
            "mean Market Coverage": g["MC"].mean(),
            "mean Competitive Impact": g["CI"].mean(),
            "Patent Asset Index (PAI)": g["CI"].sum(),
            "PAI (living only)": g["CI_alive"].sum(),
        }
    ).reindex(selected_firms)
    return out


def compute_age_rescaled_pagerank(
    edges_df: pd.DataFrame,
    families_meta: pd.DataFrame,
    damping: float = 0.85,
) -> pd.DataFrame:
    """Compute PageRank on the citation DAG (citing -> cited) and rescale by priority year (Mariani et al. 2019).

    `edges_df` must have columns ['citing', 'cited'].
    `families_meta` must have columns ['docdb_family_id', 'priority_year'].
    """
    G = nx.DiGraph()
    all_nodes = set(families_meta["docdb_family_id"].astype(int))
    G.add_nodes_from(all_nodes)
    if len(edges_df):
        clean_edges = edges_df[edges_df["citing"] != edges_df["cited"]][["citing", "cited"]].drop_duplicates()
        G.add_edges_from(zip(clean_edges["citing"].astype(int), clean_edges["cited"].astype(int)))

    pr = nx.pagerank(G, alpha=damping, max_iter=200, tol=1e-7)
    df = families_meta[["docdb_family_id", "priority_year"]].drop_duplicates("docdb_family_id").copy()
    df["docdb_family_id"] = df["docdb_family_id"].astype(int)
    df["pagerank_raw"] = df["docdb_family_id"].map(pr).fillna(0.0)

    # Age-rescaled PageRank (Mariani, Medo & Lafond 2019): z-score and ratio to cohort mean within priority_year
    grp = df.groupby("priority_year")["pagerank_raw"]
    mu = grp.transform("mean")
    sigma = grp.transform("std").replace(0, np.nan)
    df["pagerank_age_ratio"] = np.where(mu > 0, df["pagerank_raw"] / mu, 1.0)
    df["pagerank_age_z"] = ((df["pagerank_raw"] - mu) / sigma).fillna(0.0)
    return df.set_index("docdb_family_id")


# ---------------------------------------------------------------------------
# Part C3: Jaffe (1986) Technological Proximity to Electrolux
# ---------------------------------------------------------------------------
def jaffe_cpc_proximity(
    client_codes: Iterable[str],
    firm_codes_map: Dict[str, Iterable[str]],
) -> pd.DataFrame:
    """Compute Jaffe (1986) cosine similarity between a client's 4-char IPC/CPC vector and each firm's vector."""
    c_counts = Counter(str(x)[:4].upper() for x in client_codes if str(x).strip())
    c_norm = float(np.sqrt(sum(v * v for v in c_counts.values())))
    rows = []
    for firm, codes in firm_codes_map.items():
        f_counts = Counter(str(x)[:4].upper() for x in codes if str(x).strip())
        f_norm = float(np.sqrt(sum(v * v for v in f_counts.values())))
        if c_norm == 0 or f_norm == 0:
            cos = 0.0
            shared = []
        else:
            dot = sum(c_counts[k] * f_counts[k] for k in set(c_counts) & set(f_counts))
            cos = dot / (c_norm * f_norm)
            shared = sorted(set(c_counts) & set(f_counts), key=lambda k: -(c_counts[k] * f_counts[k]))[:5]
        rows.append(
            {
                "firm": firm,
                "jaffe_proximity": float(cos),
                "shared_subclasses": ", ".join(shared),
                "n_firm_subclasses": len(f_counts),
            }
        )
    return pd.DataFrame(rows).set_index("firm").sort_values("jaffe_proximity", ascending=False)
