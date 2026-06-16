#!/usr/bin/env python3
"""NexHire AI - Evaluation Module.

Computes Precision@5 and NDCG@10 against a team-labeled ground-truth
dataset.

Disclaimer:
  Ground truth was manually labeled by the development team as a proof-of-concept
  evaluation. In a production deployment, labels would be sourced from historical
  recruiter accept/reject actions.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def calculate_precision_at_k(
    ranked_ids: List[str],
    ground_truth: Dict[str, float],
    k: int = 5,
    threshold: float = 2.0,
) -> float:
    """Compute Precision@K.

    Precision@K is the fraction of the top-K retrieved candidates that are
    deemed relevant (relevance score >= threshold).

    Args:
        ranked_ids: List of candidate IDs in ranked order.
        ground_truth: Dict mapping candidate_id to relevance score (e.g. 0 to 3).
        k: The rank cutoff.
        threshold: The relevance score threshold to consider a candidate relevant.

    Returns:
        A float in [0.0, 1.0].
    """
    if not ranked_ids or k <= 0:
        return 0.0

    cutoff = min(len(ranked_ids), k)
    relevant_count = 0

    for i in range(cutoff):
        cand_id = ranked_ids[i]
        relevance = ground_truth.get(cand_id, 0.0)
        if relevance >= threshold:
            relevant_count += 1

    return relevant_count / k


def calculate_ndcg_at_k(
    ranked_ids: List[str],
    ground_truth: Dict[str, float],
    k: int = 10,
) -> float:
    """Compute Normalized Discounted Cumulative Gain (NDCG) at K.

    DCG@K = Sum_{i=1}^K [ (2^rel_i - 1) / log2(i + 1) ]
    IDCG@K = Same sum but sorted descending by relevance.

    Args:
        ranked_ids: List of candidate IDs in ranked order.
        ground_truth: Dict mapping candidate_id to relevance score.
        k: The rank cutoff.

    Returns:
        A float in [0.0, 1.0].
    """
    if not ranked_ids or k <= 0:
        return 0.0

    cutoff = min(len(ranked_ids), k)
    
    # Calculate DCG
    dcg = 0.0
    for i in range(cutoff):
        cand_id = ranked_ids[i]
        rel = ground_truth.get(cand_id, 0.0)
        # 1-based index for formula is i + 1, so log2(i + 2)
        dcg += (2**rel - 1) / math.log2(i + 2)

    # Calculate IDCG (Ideal DCG)
    # Get all possible relevance scores in the ground truth, sorted descending
    all_relevances = sorted(ground_truth.values(), reverse=True)
    idcg_cutoff = min(len(all_relevances), k)
    
    idcg = 0.0
    for i in range(idcg_cutoff):
        rel = all_relevances[i]
        idcg += (2**rel - 1) / math.log2(i + 2)

    if idcg == 0.0:
        return 0.0

    return dcg / idcg


def evaluate_pipeline(
    ranked_candidates: List[Dict[str, Any]],
    ground_truth_path: str,
) -> Dict[str, float]:
    """Evaluate pipeline ranking against ground truth labels.

    Args:
        ranked_candidates: Ranked list of candidate dicts (must contain 'candidate_id' or 'id').
        ground_truth_path: Path to the JSON file containing ground-truth relevance labels.

    Returns:
        Dict with 'precision@5' and 'ndcg@10'.
    """
    logger.info("Evaluating pipeline against ground truth: %s", ground_truth_path)
    logger.warning(
        "DISCLAIMER: Ground truth was manually labeled by the development team as a proof-of-concept. "
        "Consistency metrics only, not absolute production accuracy."
    )

    path = Path(ground_truth_path)
    if not path.exists():
        logger.error("Ground truth file not found at %s. Returning 0.0 metrics.", ground_truth_path)
        return {"precision@5": 0.0, "ndcg@10": 0.0}

    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        
        # Ground truth could be candidate_id -> relevance, or a list of items
        # Standardize to dict of candidate_id -> relevance
        ground_truth: Dict[str, float] = {}
        if isinstance(data, dict):
            for k, v in data.items():
                ground_truth[str(k)] = float(v)
        elif isinstance(data, list):
            for item in data:
                cid = item.get("candidate_id") or item.get("id")
                rel = item.get("relevance") or item.get("score", 0.0)
                if cid is not None:
                    ground_truth[str(cid)] = float(rel)
        else:
            raise ValueError("Invalid ground truth file format.")
            
    except Exception as e:
        logger.error("Error reading ground truth file: %s. Returning 0.0 metrics.", e)
        return {"precision@5": 0.0, "ndcg@10": 0.0}

    # Extract ranked candidate IDs
    ranked_ids = []
    for cand in ranked_candidates:
        cid = cand.get("candidate_id") or cand.get("id")
        if cid is not None:
            ranked_ids.append(str(cid))

    p5 = calculate_precision_at_k(ranked_ids, ground_truth, k=5, threshold=2.0)
    ndcg10 = calculate_ndcg_at_k(ranked_ids, ground_truth, k=10)

    logger.info("Evaluation complete: Precision@5 = %.2f, NDCG@10 = %.4f", p5, ndcg10)

    return {
        "precision@5": p5,
        "ndcg@10": ndcg10
    }
