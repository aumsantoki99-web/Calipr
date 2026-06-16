#!/usr/bin/env python3
"""NexHire AI - Hybrid Retrieval Module.

Combines dense (FAISS) and sparse (BM25) retrieval with Reciprocal Rank
Fusion and deduplication to produce a merged candidate shortlist.

Uses ``faiss-cpu`` for vector search — **not** Supabase / pgvector.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple

import faiss
import numpy as np
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dense retrieval — FAISS
# ---------------------------------------------------------------------------


def build_faiss_index(embeddings: List[List[float]]) -> faiss.IndexFlatIP:
    """Build a FAISS inner-product index from a list of embedding vectors.

    Vectors are L2-normalised before insertion so that inner-product
    search is equivalent to cosine similarity.

    Args:
        embeddings: List of embedding vectors (one per document).

    Returns:
        A ``faiss.IndexFlatIP`` populated with normalised vectors.

    Raises:
        ValueError: If *embeddings* is empty.
    """
    if not embeddings:
        raise ValueError("Cannot build FAISS index from an empty embedding list.")

    matrix = np.array(embeddings, dtype=np.float32)
    faiss.normalize_L2(matrix)

    dim = matrix.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(matrix)

    logger.info("Built FAISS index: %d vectors, dim=%d", matrix.shape[0], dim)
    return index


def faiss_search(
    index: faiss.IndexFlatIP,
    query_embedding: List[float],
    k: int = 20,
) -> List[Tuple[int, float]]:
    """Search the FAISS index for the *k* nearest neighbours.

    Args:
        index: A pre-built FAISS inner-product index.
        query_embedding: The query vector.
        k: Number of results to return.

    Returns:
        List of ``(doc_id, score)`` tuples sorted by descending score.
    """
    query = np.array([query_embedding], dtype=np.float32)
    faiss.normalize_L2(query)

    # Clamp k to the number of indexed vectors.
    k = min(k, index.ntotal)
    if k == 0:
        return []

    scores, ids = index.search(query, k)
    results: List[Tuple[int, float]] = []
    for score, doc_id in zip(scores[0], ids[0]):
        if doc_id >= 0:  # FAISS returns -1 for padding.
            results.append((int(doc_id), float(score)))

    logger.debug("FAISS search returned %d results (k=%d).", len(results), k)
    return results


# ---------------------------------------------------------------------------
# Sparse retrieval — BM25
# ---------------------------------------------------------------------------


def bm25_search(
    corpus: List[str],
    query: str,
    k: int = 20,
) -> List[Tuple[int, float]]:
    """Run BM25Okapi sparse retrieval over the *corpus*.

    Tokenisation is simple whitespace-split + lowercasing.

    Args:
        corpus: List of document strings (e.g. resume texts).
        query: The search query string.
        k: Number of top results to return.

    Returns:
        List of ``(doc_id, score)`` tuples sorted by descending score.
    """
    if not corpus:
        return []

    tokenised_corpus = [doc.lower().split() for doc in corpus]
    bm25 = BM25Okapi(tokenised_corpus)

    tokenised_query = query.lower().split()
    raw_scores = bm25.get_scores(tokenised_query)

    # Pair each doc_id with its score and sort descending.
    scored = [(idx, float(s)) for idx, s in enumerate(raw_scores)]
    scored.sort(key=lambda x: x[1], reverse=True)

    results = scored[:k]
    logger.debug("BM25 search returned %d results (k=%d).", len(results), k)
    return results


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion (RRF)
# ---------------------------------------------------------------------------


def reciprocal_rank_fusion(
    result_lists: List[List[Tuple[int, float]]],
    k: int = 60,
) -> List[Tuple[int, float]]:
    """Fuse multiple ranked result lists using Reciprocal Rank Fusion.

    For each document, the fused score is::

        score = Σ  1 / (k + rank_i)

    where *rank_i* is the 1-based rank of the document in the *i*-th
    list and *k* is a constant (default 60).

    Args:
        result_lists: List of ranked result lists.  Each inner list
            contains ``(doc_id, score)`` tuples in descending score order.
        k: RRF constant — higher values dampen rank differences.

    Returns:
        Fused ``(doc_id, fused_score)`` tuples sorted descending.
    """
    fused_scores: Dict[int, float] = {}

    for result_list in result_lists:
        for rank, (doc_id, _score) in enumerate(result_list, start=1):
            fused_scores[doc_id] = fused_scores.get(doc_id, 0.0) + 1.0 / (k + rank)

    fused = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    logger.debug("RRF produced %d fused results.", len(fused))
    return fused


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def deduplicate_results(
    results: List[Tuple[int, float]],
) -> List[Tuple[int, float]]:
    """Remove duplicate doc_ids, keeping the highest-scored occurrence.

    Args:
        results: ``(doc_id, score)`` tuples (need not be sorted).

    Returns:
        Deduplicated list sorted by descending score.
    """
    best: Dict[int, float] = {}
    for doc_id, score in results:
        if doc_id not in best or score > best[doc_id]:
            best[doc_id] = score

    deduped = sorted(best.items(), key=lambda x: x[1], reverse=True)
    logger.debug("Dedup: %d -> %d results.", len(results), len(deduped))
    return deduped


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def hybrid_retrieve(
    faiss_index: faiss.IndexFlatIP,
    query_embedding: List[float],
    corpus: List[str],
    query_text: str,
    k: int = 20,
) -> List[Tuple[int, float]]:
    """Run the full hybrid retrieval pipeline.

    Steps:
      1. Dense search via FAISS.
      2. Sparse search via BM25.
      3. Reciprocal Rank Fusion.
      4. Deduplication.

    Args:
        faiss_index: Pre-built FAISS index over candidate embeddings.
        query_embedding: Embedding vector for the JD / query.
        corpus: List of resume texts (same order as embeddings).
        query_text: Plain-text query for BM25.
        k: Number of candidates to return.

    Returns:
        Top-*k* ``(doc_id, fused_score)`` tuples.
    """
    logger.info("Starting hybrid retrieval (k=%d).", k)

    dense_results = faiss_search(faiss_index, query_embedding, k=k * 2)
    sparse_results = bm25_search(corpus, query_text, k=k * 2)

    fused = reciprocal_rank_fusion([dense_results, sparse_results])
    deduped = deduplicate_results(fused)

    top_k = deduped[:k]
    logger.info("Hybrid retrieval complete: returning %d candidates.", len(top_k))
    return top_k
