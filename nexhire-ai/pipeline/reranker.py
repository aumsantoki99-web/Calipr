#!/usr/bin/env python3
"""NexHire AI - Agentic Re-ranker.

Performs LLM-powered re-ranking of candidates with safety guards:
  * Resume truncation to 200-char summaries (never sends full text).
  * Fallback to Phase 3 composite ranking if the LLM call fails.
  * ``max_retries=2`` on LLM HTTP calls.
  * ``max_iterations=5`` guard on any tool-use loop.
  * Config-driven provider switch between **Groq** and **Gemini**.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Resume truncation
# ---------------------------------------------------------------------------


def truncate_resume(resume_text: str, max_chars: int = 200) -> str:
    """Return a truncated summary of a resume.

    Keeps the first *max_chars* characters and appends an ellipsis if the
    text was shortened.  This ensures we never send full resumes to the
    LLM, reducing cost and latency.

    Args:
        resume_text: Full resume text.
        max_chars: Maximum character count for the summary.

    Returns:
        Truncated string.
    """
    if not resume_text:
        return ""
    text = resume_text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def build_rerank_prompt(jd_summary: str, candidates: List[Dict[str, Any]]) -> str:
    """Build the re-ranking prompt for the LLM.

    Each candidate entry includes a 200-char resume summary, their
    composite score, and key skills — **not** the full resume.

    Args:
        jd_summary: A short summary of the job description.
        candidates: List of candidate dicts; each should have at minimum
            ``candidate_id``, ``resume_text``, ``composite_score``, and
            ``skills``.

    Returns:
        A prompt string ready to be sent to the LLM.
    """
    candidate_block_parts: List[str] = []
    for idx, c in enumerate(candidates, start=1):
        summary = truncate_resume(c.get("resume_text", ""), max_chars=200)
        skills = ", ".join(c.get("skills", [])[:10])
        score = c.get("composite_score", 0.0)
        cid = c.get("candidate_id", f"candidate_{idx}")
        candidate_block_parts.append(
            f"  {idx}. ID: {cid}\n"
            f"     Score: {score:.3f}\n"
            f"     Skills: {skills}\n"
            f"     Resume snippet: {summary}"
        )

    candidate_block = "\n".join(candidate_block_parts)

    prompt = (
        "You are an expert technical recruiter. Re-rank the following "
        "candidates for the job described below. Return a JSON array of "
        "objects with keys: candidate_id, rank, rationale.\n\n"
        f"## Job Description\n{jd_summary}\n\n"
        f"## Candidates\n{candidate_block}\n\n"
        "Return ONLY valid JSON — no markdown fences, no commentary."
    )
    return prompt


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) from LLM output."""
    text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"\n?```\s*$", "", text.strip(), flags=re.MULTILINE)
    return text.strip()


def parse_rerank_response(
    response_text: str,
    candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Parse and validate the LLM's re-ranking response.

    Strips markdown code fences before attempting ``json.loads()``.

    Args:
        response_text: Raw LLM response string.
        candidates: Original candidate list (used as fallback reference).

    Returns:
        List of dicts with ``candidate_id``, ``rank``, ``rationale``.

    Raises:
        ValueError: If the response cannot be parsed into valid JSON or
            does not contain the expected structure.
    """
    cleaned = _strip_code_fences(response_text)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM response is not valid JSON: {exc}") from exc

    if not isinstance(parsed, list):
        raise ValueError("Expected a JSON array from the LLM.")

    # Validate each entry.
    results: List[Dict[str, Any]] = []
    for entry in parsed:
        if not isinstance(entry, dict) or "candidate_id" not in entry:
            continue
        results.append(
            {
                "candidate_id": entry["candidate_id"],
                "rank": entry.get("rank", len(results) + 1),
                "rationale": entry.get("rationale", "No rationale provided."),
            }
        )

    if not results:
        raise ValueError("Parsed JSON contained no valid candidate entries.")

    return results


# ---------------------------------------------------------------------------
# Fallback ranking
# ---------------------------------------------------------------------------


def fallback_ranking(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return candidates sorted by their Phase 3 composite score.

    Used when the LLM call fails after all retries.  Each candidate
    receives a generic rationale indicating the LLM was unavailable.

    Args:
        candidates: Candidate list with ``composite_score`` field.

    Returns:
        Re-ordered candidate list with ``rank`` and ``rationale`` added.
    """
    sorted_candidates = sorted(
        candidates,
        key=lambda c: c.get("composite_score", 0.0),
        reverse=True,
    )
    results: List[Dict[str, Any]] = []
    for rank, c in enumerate(sorted_candidates, start=1):
        results.append(
            {
                "candidate_id": c.get("candidate_id", "unknown"),
                "rank": rank,
                "rationale": "Ranked by composite score (LLM unavailable).",
                **{k: v for k, v in c.items() if k != "candidate_id"},
            }
        )
    logger.warning("Using fallback ranking (LLM unavailable).")
    return results


# ---------------------------------------------------------------------------
# LLM call — supports Groq and Gemini
# ---------------------------------------------------------------------------


def call_llm(
    prompt: str,
    provider: str = "groq",
    config: Optional[Dict[str, Any]] = None,
) -> str:
    """Call an LLM provider and return the response text.

    Supports two providers via a config switch:
      * ``groq`` — uses the ``groq`` Python SDK.
      * ``gemini`` — uses ``google.generativeai``.

    Args:
        prompt: The prompt string.
        provider: ``'groq'`` or ``'gemini'``.
        config: Dict with ``api_key``, ``model_name``, etc.  If not
            provided, keys are read from environment variables.

    Returns:
        The LLM's response text.

    Raises:
        RuntimeError: If the LLM call fails.
    """
    config = config or {}
    provider = provider.lower()

    if provider == "groq":
        return _call_groq(prompt, config)
    elif provider == "gemini":
        return _call_gemini(prompt, config)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider!r}.  Use 'groq' or 'gemini'.")


def _call_groq(prompt: str, config: Dict[str, Any]) -> str:
    """Call Groq LLM."""
    try:
        from groq import Groq  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("groq package is not installed.  Run: pip install groq") from exc

    api_key = config.get("api_key") or os.getenv("GROQ_API_KEY", "")
    model = config.get("model_name") or os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set.")

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=2048,
    )
    return response.choices[0].message.content or ""


def _call_gemini(prompt: str, config: Dict[str, Any]) -> str:
    """Call Google Gemini LLM."""
    try:
        import google.generativeai as genai  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "google-generativeai package is not installed.  "
            "Run: pip install google-generativeai"
        ) from exc

    api_key = config.get("api_key") or os.getenv("GEMINI_API_KEY", "")
    model_name = config.get("model_name") or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    return response.text or ""


# ---------------------------------------------------------------------------
# Agentic re-ranking — main entry point
# ---------------------------------------------------------------------------


def agentic_rerank(
    jd_summary: str,
    candidates: List[Dict[str, Any]],
    provider: str = "groq",
    config: Optional[Dict[str, Any]] = None,
    max_retries: int = 2,
    max_iterations: int = 5,
) -> List[Dict[str, Any]]:
    """Agentic re-ranking with LLM, retries, and iteration guards.

    Workflow:
      1. Build re-rank prompt (truncated resumes).
      2. Call LLM with up to *max_retries* attempts.
      3. Parse and validate the response.
      4. If anything fails, fall back to ``fallback_ranking``.

    The *max_iterations* parameter guards against run-away tool-use
    loops in future agentic expansions.

    Args:
        jd_summary: Short JD summary text.
        candidates: Candidate dicts with scores and resume text.
        provider: ``'groq'`` or ``'gemini'``.
        config: Provider-specific configuration dict.
        max_retries: Maximum LLM call retries on failure.
        max_iterations: Hard cap on tool-use loop iterations.

    Returns:
        Re-ranked list of candidate dicts with ``rank`` and ``rationale``.
    """
    if not candidates:
        logger.warning("No candidates to re-rank.")
        return []

    prompt = build_rerank_prompt(jd_summary, candidates)

    for iteration in range(max_iterations):
        logger.debug("Re-rank iteration %d/%d.", iteration + 1, max_iterations)

        last_error: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                logger.info(
                    "LLM call attempt %d/%d (provider=%s).",
                    attempt + 1,
                    max_retries + 1,
                    provider,
                )
                response_text = call_llm(prompt, provider=provider, config=config)
                ranked = parse_rerank_response(response_text, candidates)
                logger.info("Agentic re-rank succeeded on iteration %d.", iteration + 1)
                return ranked
            except Exception as exc:
                last_error = exc
                logger.warning("LLM attempt %d failed: %s", attempt + 1, exc)

        # All retries exhausted for this iteration.
        logger.error(
            "All %d retries exhausted on iteration %d: %s",
            max_retries + 1,
            iteration + 1,
            last_error,
        )
        break  # Don't loop further — fall back.

    logger.error("Agentic re-rank failed; using fallback ranking.")
    return fallback_ranking(candidates)
