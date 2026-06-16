#!/usr/bin/env python3
"""NexHire AI - Ingestion Module.

Handles candidate and JD loading with:
  * JSON-Schema validation (``jsonschema``).
  * LLM-assisted JD parsing.
  * Markdown code-fence stripping before ``json.loads()``.
  * Pre-filtering by ``years_experience``.
  * Deduplication by email.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import jsonschema

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schema handling
# ---------------------------------------------------------------------------


def load_candidate_schema(schema_path: str) -> Dict[str, Any]:
    """Load a JSON Schema from *schema_path*.

    Args:
        schema_path: Absolute or relative path to the JSON Schema file.

    Returns:
        Parsed schema as a Python dict.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    path = Path(schema_path)
    if not path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(path, "r", encoding="utf-8") as fh:
        schema = json.load(fh)
    logger.info("Loaded candidate schema from %s.", schema_path)
    return schema


def validate_candidate(
    candidate: Dict[str, Any],
    schema: Dict[str, Any],
) -> Tuple[bool, List[str]]:
    """Validate a single candidate profile against a JSON Schema.

    Args:
        candidate: Candidate data dict.
        schema: JSON Schema dict.

    Returns:
        Tuple of ``(is_valid, errors)`` where *errors* is a list of
        human-readable validation error messages.
    """
    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(candidate), key=lambda e: list(e.path))
    error_messages = [f"{'.'.join(str(p) for p in e.absolute_path) or '(root)'}: {e.message}" for e in errors]

    if error_messages:
        logger.debug(
            "Candidate %s failed validation: %s",
            candidate.get("candidate_id", "unknown"),
            error_messages,
        )
        return False, error_messages

    return True, []


# ---------------------------------------------------------------------------
# Code-fence stripping
# ---------------------------------------------------------------------------


def strip_code_fences(text: str) -> str:
    """Remove markdown code fences from LLM output.

    Handles patterns like:
      * ````json ... ````
      * ```` ... ````

    Args:
        text: Raw LLM output string.

    Returns:
        Cleaned string suitable for ``json.loads()``.
    """
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n?```\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


# ---------------------------------------------------------------------------
# JD parsing with LLM
# ---------------------------------------------------------------------------


def parse_jd_with_llm(
    jd_text: str,
    provider: str = "groq",
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Parse a raw job description into structured fields using an LLM.

    Extracts: ``title``, ``required_skills``, ``preferred_skills``,
    ``min_years``, ``domain``, ``summary``, ``level``.

    Args:
        jd_text: Raw JD text.
        provider: LLM provider (``'groq'`` or ``'gemini'``).
        config: Provider-specific config dict.

    Returns:
        Dict of parsed JD fields.

    Raises:
        RuntimeError: If the LLM call or parsing fails.
    """
    # Import the reranker's call_llm to avoid duplicating LLM wrappers.
    try:
        from pipeline.reranker import call_llm as _call_llm
    except ImportError:
        from nexhire_ai.pipeline.reranker import call_llm as _call_llm  # type: ignore[import-untyped]


    prompt = (
        "Extract the following fields from the job description below and "
        "return them as a JSON object.  Fields: title (string), "
        "required_skills (array of strings), preferred_skills (array of "
        "strings), min_years (integer), domain (string), summary (string), "
        "level (string: one of intern/junior/mid/senior/lead/staff/"
        "principal/director).\n\n"
        "Return ONLY valid JSON — no markdown fences, no commentary.\n\n"
        f"## Job Description\n{jd_text}"
    )

    try:
        response = _call_llm(prompt, provider=provider, config=config)
        cleaned = strip_code_fences(response)
        parsed = json.loads(cleaned)
        logger.info("Parsed JD successfully: title=%s", parsed.get("title"))
        return parsed
    except Exception as exc:
        logger.error("Failed to parse JD with LLM: %s", exc)
        # Return a minimal fallback.
        return {
            "title": "",
            "required_skills": [],
            "preferred_skills": [],
            "min_years": 0,
            "domain": "",
            "summary": jd_text[:500],
            "level": "mid",
        }


# ---------------------------------------------------------------------------
# Pre-filtering and deduplication
# ---------------------------------------------------------------------------


def pre_filter_candidates(
    candidates: List[Dict[str, Any]],
    min_years: int = 0,
) -> List[Dict[str, Any]]:
    """Filter candidates by minimum years of experience.

    Args:
        candidates: List of candidate dicts.
        min_years: Minimum required years of experience.

    Returns:
        Filtered list retaining only candidates with
        ``years_experience >= min_years``.
    """
    if min_years <= 0:
        return candidates

    filtered = [
        c
        for c in candidates
        if c.get("years_experience", 0) >= min_years
    ]
    logger.info(
        "Pre-filter: %d → %d candidates (min_years=%d).",
        len(candidates),
        len(filtered),
        min_years,
    )
    return filtered


def deduplicate_by_email(
    candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Remove duplicate candidates by email, keeping the first occurrence.

    Args:
        candidates: List of candidate dicts.

    Returns:
        Deduplicated list.
    """
    seen_emails: set[str] = set()
    unique: List[Dict[str, Any]] = []

    for c in candidates:
        email = c.get("email", "").lower().strip()
        if not email:
            unique.append(c)  # Keep candidates without email.
            continue
        if email not in seen_emails:
            seen_emails.add(email)
            unique.append(c)

    logger.info(
        "Dedup by email: %d -> %d candidates.",
        len(candidates),
        len(unique),
    )
    return unique


# ---------------------------------------------------------------------------
# Full ingestion pipeline
# ---------------------------------------------------------------------------


def load_candidates(
    file_path: str,
    schema_path: Optional[str] = None,
    min_years: int = 0,
) -> List[Dict[str, Any]]:
    """Load, validate, filter, and deduplicate candidates from a JSON file.

    Pipeline steps:
      1. Load raw JSON array from *file_path*.
      2. Validate each candidate against schema (if provided).
      3. Pre-filter by ``years_experience``.
      4. Deduplicate by email.

    Args:
        file_path: Path to the candidates JSON file.
        schema_path: Optional path to the candidate JSON Schema.
        min_years: Minimum years of experience filter.

    Returns:
        List of validated and cleaned candidate dicts.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Candidates file not found: {file_path}")

    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)

    if not isinstance(raw, list):
        raise ValueError(f"Expected a JSON array in {file_path}, got {type(raw).__name__}.")

    logger.info("Loaded %d raw candidates from %s.", len(raw), file_path)

    # Schema validation.
    schema: Optional[Dict[str, Any]] = None
    if schema_path:
        schema = load_candidate_schema(schema_path)

    valid_candidates: List[Dict[str, Any]] = []
    for idx, candidate in enumerate(raw):
        if schema:
            is_valid, errors = validate_candidate(candidate, schema)
            if not is_valid:
                logger.warning(
                    "Candidate %d (%s) failed validation: %s",
                    idx,
                    candidate.get("candidate_id", "unknown"),
                    errors,
                )
                continue
        valid_candidates.append(candidate)

    logger.info("Validated: %d / %d candidates passed schema checks.", len(valid_candidates), len(raw))

    # Pre-filter.
    filtered = pre_filter_candidates(valid_candidates, min_years=min_years)

    # Deduplicate.
    deduped = deduplicate_by_email(filtered)

    return deduped


def load_jd(
    file_path: Optional[str] = None,
    jd_text: Optional[str] = None,
    provider: str = "groq",
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Load and parse a job description from file or inline text.

    If both *file_path* and *jd_text* are provided, *file_path* takes
    precedence.

    Args:
        file_path: Path to a plaintext JD file.
        jd_text: Inline JD text string.
        provider: LLM provider for JD parsing.
        config: Provider-specific config dict.

    Returns:
        Parsed JD dict with structured fields.

    Raises:
        ValueError: If neither *file_path* nor *jd_text* is provided.
    """
    if file_path:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"JD file not found: {file_path}")
        with open(path, "r", encoding="utf-8") as fh:
            jd_text = fh.read()
    elif not jd_text:
        raise ValueError("Either file_path or jd_text must be provided.")

    logger.info("Parsing JD (%d chars) with LLM provider=%s.", len(jd_text or ""), provider)
    return parse_jd_with_llm(jd_text, provider=provider, config=config)  # type: ignore[arg-type]
