#!/usr/bin/env python3
"""NexHire AI - 5-Signal Scoring Engine.

Implements the composite scoring pipeline with five independent signals:
  1. Semantic Fit        (cosine similarity of embeddings)
  2. Skills Match        (manual hit-counting + adjacency map — NO BM25)
  3. Career Trajectory   (experience, progression, education)
  4. Behavioral          (leadership, conflict-resolution, collaboration)
  5. Domain Alignment    (industry-domain overlap)

Each signal returns a float in [0, 1].  ``compute_final_score`` blends them
with configurable weights.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Seniority level map — maps keywords found in job titles to ordinal ranks.
# Includes 'associate' and 'entry' as required by the strategy review.
LEVEL_MAP: Dict[str, int] = {
    "intern": 0,
    "entry": 1,
    "junior": 1,
    "associate": 2,
    "mid": 3,
    "senior": 4,
    "lead": 5,
    "staff": 6,
    "principal": 7,
    "director": 8,
    "vp": 9,
    "head": 9,
    "chief": 10,
    "cto": 10,
    "ceo": 10,
}

DEFAULT_WEIGHTS: Dict[str, float] = {
    "semantic": 0.25,
    "skills": 0.30,
    "trajectory": 0.20,
    "behavioral": 0.10,
    "domain": 0.15,
}

# Education-level scoring lookup.
EDUCATION_SCORES: Dict[str, float] = {
    "phd": 1.0,
    "doctorate": 1.0,
    "masters": 0.8,
    "master": 0.8,
    "mba": 0.8,
    "bachelors": 0.6,
    "bachelor": 0.6,
    "associate": 0.4,
    "diploma": 0.3,
    "high school": 0.1,
}


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp *value* to the closed interval [lo, hi]."""
    return max(lo, min(hi, value))


def extract_level_keyword(title: str) -> str:
    """Extract a seniority-level keyword from a job *title*.

    Scans the title (case-insensitive) for any key present in
    ``LEVEL_MAP`` and returns the first match.  Falls back to ``'mid'``
    if no keyword is recognised.

    Args:
        title: A job title string, e.g. "Senior Software Engineer".

    Returns:
        A lowercase keyword such as ``'senior'``, ``'lead'``, etc.
    """
    if not title:
        return "mid"
    title_lower = title.lower()
    # Check in descending specificity (longer keywords first).
    for keyword in sorted(LEVEL_MAP.keys(), key=len, reverse=True):
        if keyword in title_lower:
            return keyword
    return "mid"


# ---------------------------------------------------------------------------
# Signal 1 — Semantic Fit
# ---------------------------------------------------------------------------


def semantic_fit_score(
    jd_embedding: List[float],
    resume_embedding: List[float],
) -> float:
    """Cosine similarity between JD and resume embedding vectors.

    Args:
        jd_embedding: Embedding vector for the job description.
        resume_embedding: Embedding vector for the candidate's resume.

    Returns:
        A float in [0, 1] representing semantic similarity.
    """
    try:
        jd_vec = np.array(jd_embedding, dtype=np.float32)
        res_vec = np.array(resume_embedding, dtype=np.float32)

        dot = float(np.dot(jd_vec, res_vec))
        norm_jd = float(np.linalg.norm(jd_vec))
        norm_res = float(np.linalg.norm(res_vec))

        if norm_jd == 0.0 or norm_res == 0.0:
            logger.warning("Zero-norm embedding detected; returning 0.0.")
            return 0.0

        similarity = dot / (norm_jd * norm_res)
        return _clamp(similarity)
    except Exception:
        logger.exception("Error computing semantic fit score.")
        return 0.0


# ---------------------------------------------------------------------------
# Signal 2 — Skills Match  (manual hit-counting + adjacency — NO BM25)
# ---------------------------------------------------------------------------


def skills_match_score(
    jd_skills: List[str],
    resume_skills: List[str],
    adjacency_map: Optional[Dict[str, List[str]]] = None,
) -> float:
    """Score how well a candidate's skills cover the JD requirements.

    Uses **manual hit-counting only** (BM25 is intentionally excluded per
    the strategy review).  For each required JD skill the scorer checks:

    1. **Direct match** — the skill appears in the resume skills list
       (case-insensitive).
    2. **Adjacent match** — one of the skill's neighbours in the
       adjacency map appears in the resume skills list.

    Adjacent hits are weighted at half a direct hit (0.5).

    Args:
        jd_skills: Skills required by the JD.
        resume_skills: Skills listed on the candidate's resume.
        adjacency_map: Mapping of skill → related skills.

    Returns:
        A float in [0, 1].
    """
    if not jd_skills:
        logger.debug("No JD skills provided; returning 1.0.")
        return 1.0

    adjacency_map = adjacency_map or {}
    resume_lower = {s.lower().strip() for s in resume_skills}

    direct_hits = 0
    adjacent_hits = 0

    for skill in jd_skills:
        skill_lower = skill.lower().strip()
        if skill_lower in resume_lower:
            direct_hits += 1
            continue

        # Check adjacency map for related skills.
        neighbours = adjacency_map.get(skill_lower, [])
        found_adjacent = False
        for neighbour in neighbours:
            if neighbour.lower().strip() in resume_lower:
                found_adjacent = True
                break
        if found_adjacent:
            adjacent_hits += 1

    total_required = len(jd_skills)
    score = (direct_hits + 0.5 * adjacent_hits) / total_required
    logger.debug(
        "Skills match: %d direct, %d adjacent out of %d required -> %.3f",
        direct_hits,
        adjacent_hits,
        total_required,
        score,
    )
    return _clamp(score)


# ---------------------------------------------------------------------------
# Signal 3 — Career Trajectory
# ---------------------------------------------------------------------------


def career_trajectory_score(candidate: Dict[str, Any]) -> float:
    """Score career trajectory based on experience, progression, education.

    Sub-components (each in [0, 1], averaged):
      * **Experience depth** — years_experience normalised to 15-year cap.
      * **Progression** — ratio of distinct seniority levels across
        current + previous titles.
      * **Education** — degree-level lookup.

    Args:
        candidate: Candidate profile dictionary.

    Returns:
        A float in [0, 1].
    """
    try:
        # --- Experience depth ---
        years = float(candidate.get("years_experience", 0))
        experience_score = _clamp(years / 15.0)

        # --- Title progression ---
        titles: List[str] = []
        current = candidate.get("current_title", "")
        if current:
            titles.append(current)
        titles.extend(candidate.get("previous_titles", []))

        if titles:
            levels = {LEVEL_MAP.get(extract_level_keyword(t), 3) for t in titles}
            # More distinct levels ⇒ stronger progression.
            progression_score = _clamp(len(levels) / 4.0)
        else:
            progression_score = 0.0

        # --- Education ---
        education = candidate.get("education", {})
        degree = (education.get("degree", "") if isinstance(education, dict) else "").lower()
        education_score = 0.0
        for key, val in EDUCATION_SCORES.items():
            if key in degree:
                education_score = val
                break

        # Weighted average of sub-components.
        score = 0.40 * experience_score + 0.35 * progression_score + 0.25 * education_score
        logger.debug(
            "Trajectory: exp=%.2f prog=%.2f edu=%.2f -> %.3f",
            experience_score,
            progression_score,
            education_score,
            score,
        )
        return _clamp(score)
    except Exception:
        logger.exception("Error computing career trajectory score.")
        return 0.0


# ---------------------------------------------------------------------------
# Signal 4 — Behavioral
# ---------------------------------------------------------------------------

_BEHAVIORAL_FIELDS = ("leadership_examples", "conflict_resolution", "collaboration_style")


def behavioral_score(candidate: Dict[str, Any]) -> float:
    """Score based on presence and quality of behavioural data.

    Each of the three behavioural fields (``leadership_examples``,
    ``conflict_resolution``, ``collaboration_style``) contributes ≈0.33
    when present and non-empty.

    Args:
        candidate: Candidate profile dictionary.

    Returns:
        A float in [0, 1].
    """
    try:
        present = 0
        for field in _BEHAVIORAL_FIELDS:
            value = candidate.get(field, "")
            if isinstance(value, str) and value.strip():
                present += 1
        score = present / len(_BEHAVIORAL_FIELDS)
        logger.debug("Behavioral: %d/%d fields present -> %.3f", present, len(_BEHAVIORAL_FIELDS), score)
        return _clamp(score)
    except Exception:
        logger.exception("Error computing behavioral score.")
        return 0.0


# ---------------------------------------------------------------------------
# Signal 5 — Domain Alignment
# ---------------------------------------------------------------------------


def domain_alignment_score(
    jd_domain: str,
    candidate_domains: List[str],
) -> float:
    """Score domain overlap between the JD and the candidate.

    * **Exact match** (case-insensitive) → 1.0
    * **Partial / substring match** → 0.5
    * **No match** → 0.0

    Args:
        jd_domain: The target domain from the JD.
        candidate_domains: Domains the candidate has experience in.

    Returns:
        A float in {0.0, 0.5, 1.0}.
    """
    if not jd_domain or not candidate_domains:
        return 0.0

    jd_lower = jd_domain.lower().strip()
    candidate_lower = [d.lower().strip() for d in candidate_domains]

    # Exact match.
    if jd_lower in candidate_lower:
        return 1.0

    # Partial / substring match.
    for domain in candidate_lower:
        if jd_lower in domain or domain in jd_lower:
            return 0.5

    return 0.0


# ---------------------------------------------------------------------------
# Composite Score
# ---------------------------------------------------------------------------


def compute_final_score(
    scores: Dict[str, float],
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """Compute the weighted composite score from all five signals.

    Args:
        scores: Dict mapping signal names to their [0, 1] scores.
            Expected keys: ``semantic``, ``skills``, ``trajectory``,
            ``behavioral``, ``domain``.
        weights: Optional custom weight dict.  Defaults to
            ``DEFAULT_WEIGHTS``.

    Returns:
        A float in [0, 1] representing the overall candidate fit.
    """
    w = weights or DEFAULT_WEIGHTS

    total_weight = sum(w.values())
    if total_weight == 0:
        logger.error("All weights are zero; returning 0.0.")
        return 0.0

    composite = sum(scores.get(signal, 0.0) * w.get(signal, 0.0) for signal in w)
    # Normalise in case weights don't sum to 1.
    composite /= total_weight

    logger.info("Final composite score: %.4f  (signals=%s)", composite, scores)
    return _clamp(composite)
