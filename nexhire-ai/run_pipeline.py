#!/usr/bin/env python3
"""NexHire AI Recruiter — One-click pipeline execution script.

Runs the entire 4-phase recruitment pipeline:
  Phase 1: Ingest & Parse
  Phase 2: Hybrid Retrieval (FAISS + BM25 + RRF)
  Phase 3: 5-Signal Scoring
  Phase 4: Agentic Re-Rank (Groq/Gemini LLM)
  (Optional) Phase 5: Evaluation (Precision@5 and NDCG@10)
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Add the current directory to sys.path to allow absolute imports of pipeline modules
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from dotenv import load_dotenv
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("run_pipeline")

# Import pipeline components
try:
    from pipeline.ingest import load_candidates, load_jd
    from pipeline.retrieval import build_faiss_index, hybrid_retrieve
    from pipeline.scoring import (
        semantic_fit_score,
        skills_match_score,
        career_trajectory_score,
        behavioral_score,
        domain_alignment_score,
        compute_final_score
    )
    from pipeline.reranker import agentic_rerank
    from pipeline.evaluate import evaluate_pipeline
except ImportError as exc:
    logger.error("Failed to import pipeline modules: %s", exc)
    logger.error("Make sure you are running this script from the nexhire-ai/ directory.")
    sys.exit(1)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="NexHire AI Recruiter Pipeline")
    parser.add_argument(
        "--jd",
        default="data/job_description.txt",
        help="Path to the plaintext job description file (default: data/job_description.txt)"
    )
    parser.add_argument(
        "--candidates",
        default="data/candidates.json",
        help="Path to the candidates JSON database file (default: data/candidates.json)"
    )
    parser.add_argument(
        "--output",
        default="outputs/shortlist.csv",
        help="Path to save the output ranked shortlist CSV (default: outputs/shortlist.csv)"
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        help="Run evaluation against test ground truth labels"
    )
    parser.add_argument(
        "--test-ground-truth",
        default="data/test_candidates.json",
        help="Path to the test ground truth labels JSON file (default: data/test_candidates.json)"
    )
    parser.add_argument(
        "--provider",
        default=os.getenv("LLM_PROVIDER", "groq"),
        choices=["groq", "gemini"],
        help="LLM provider for Phase 4 (groq or gemini)"
    )
    return parser.parse_args()


def get_embedding_model():
    """Load the sentence-transformer model for embedding generation.

    Falls back gracefully if the package is not installed or fails.
    """
    try:
        from sentence_transformers import SentenceTransformer
        model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        logger.info("Loading sentence-transformers model: %s", model_name)
        return SentenceTransformer(model_name)
    except Exception as e:
        logger.warning("Failed to load sentence-transformers: %s. Using fallback mock embeddings.", e)
        return None


def generate_fallback_embedding(text: str) -> List[float]:
    """Generate a deterministic mock 384-dimensional embedding vector based on hash of text."""
    import hashlib
    h = hashlib.sha256(text.encode('utf-8')).digest()
    np_rand = np_random_from_seed(int.from_bytes(h[:4], 'big'))
    vec = np_rand.tolist()
    # Normalize vector to L2 norm of 1.0
    norm = sum(x*x for x in vec) ** 0.5
    if norm == 0:
        return [0.0] * 384
    return [x / norm for x in vec]


def np_random_from_seed(seed: int):
    """Deterministic random float list generator without external numpy dependency if possible,
    but we have numpy installed so we can use it.
    """
    import numpy as np
    rng = np.random.default_rng(seed)
    return rng.normal(0.0, 1.0, 384)


def save_shortlist_csv(
    ranked_results: List[Dict[str, Any]],
    output_path: str,
    original_candidates: List[Dict[str, Any]]
) -> None:
    """Save ranked candidates shortlist to a CSV file.

    Args:
        ranked_results: Re-ranked candidate entries from Phase 4.
        output_path: Path to write the CSV file.
        original_candidates: List of candidate profiles containing metadata.
    """
    # Create lookup map
    cand_map = {c.get("candidate_id") or c.get("id"): c for c in original_candidates}
    
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "Rank", "Candidate ID", "Name", "Email", "Current Title", 
            "Years of Experience", "Composite Score", "Rationale"
        ])
        
        for item in ranked_results:
            cid = item["candidate_id"]
            rank = item["rank"]
            rationale = item["rationale"]
            
            c = cand_map.get(cid, {})
            name = c.get("name", "N/A")
            email = c.get("email", "N/A")
            title = c.get("current_title", "N/A")
            y_exp = c.get("years_experience", "N/A")
            score = c.get("composite_score", 0.0)
            
            writer.writerow([
                rank, cid, name, email, title, y_exp, f"{score:.4f}", rationale
            ])


def main() -> None:
    args = parse_arguments()
    start_time = time.time()

    logger.info("=== NEXHIRE AI RECRUITER PIPELINE INITIALIZATION ===")
    
    # -------------------------------------------------------------------------
    # PHASE 1: Ingest & Parse
    # -------------------------------------------------------------------------
    logger.info("--- PHASE 1: INGEST & PARSE ---")
    
    # Load candidate database
    schema_path = "data/candidate_schema.json"
    if not Path(schema_path).exists():
        schema_path = None  # Skip validation if schema is missing
        logger.warning("Candidate schema not found. Skipping validation.")
        
    try:
        candidates = load_candidates(args.candidates, schema_path=schema_path)
    except FileNotFoundError:
        logger.error("Candidates JSON database not found at: %s", args.candidates)
        logger.error("Please create a dummy candidates database first.")
        sys.exit(1)
        
    if not candidates:
        logger.error("No valid candidates loaded from database.")
        sys.exit(1)

    # Load job description
    try:
        jd = load_jd(file_path=args.jd, provider=args.provider)
    except FileNotFoundError:
        logger.error("Job description text file not found at: %s", args.jd)
        logger.error("Please create a job description text file first.")
        sys.exit(1)

    logger.info("Parsed Job Description:")
    logger.info("  Title: %s", jd.get("title", "N/A"))
    logger.info("  Level: %s", jd.get("level", "N/A"))
    logger.info("  Domain: %s", jd.get("domain", "N/A"))
    logger.info("  Required Skills: %s", jd.get("required_skills", []))
    logger.info("  Min Experience: %d years", jd.get("min_years", 0))

    # Pre-filter candidates by min experience from JD
    min_years = jd.get("min_years", 0)
    candidates = [c for c in candidates if c.get("years_experience", 0) >= min_years]
    logger.info("Filtered candidate pool size matching min experience (%d yrs): %d", min_years, len(candidates))
    
    if not candidates:
        logger.warning("No candidates meet the minimum experience requirement.")
        sys.exit(0)

    # Get embedding model
    embed_model = get_embedding_model()
    
    # Ensure query embedding exists
    jd_text = f"{jd.get('title', '')} {jd.get('domain', '')} " + " ".join(jd.get('required_skills', [])) + f" {jd.get('summary', '')}"
    if embed_model:
        jd_embedding = embed_model.encode(jd_text).tolist()
    else:
        jd_embedding = generate_fallback_embedding(jd_text)

    # Ensure all candidates have embeddings
    for c in candidates:
        if "resume_embedding" not in c or not c["resume_embedding"]:
            resume_text = c.get("resume_text", "")
            if embed_model:
                c["resume_embedding"] = embed_model.encode(resume_text).tolist()
            else:
                c["resume_embedding"] = generate_fallback_embedding(resume_text)

    # Load skill adjacency map
    try:
        with open("data/skill_adjacency_map.json", "r", encoding="utf-8") as fh:
            adjacency_map = json.load(fh)
    except Exception:
        logger.warning("Failed to load skill adjacency map. Operating without skill expansions.")
        adjacency_map = {}

    # -------------------------------------------------------------------------
    # PHASE 2: Hybrid Retrieval
    # -------------------------------------------------------------------------
    logger.info("--- PHASE 2: HYBRID RETRIEVAL (FAISS + BM25 + RRF) ---")
    
    # Prepare inputs for retrieval
    embeddings = [c["resume_embedding"] for c in candidates]
    corpus = [c.get("resume_text", "") for c in candidates]
    query_text = jd_text
    
    faiss_index = build_faiss_index(embeddings)
    
    # Retrieve top 50 candidates
    retrieved_tuples = hybrid_retrieve(
        faiss_index=faiss_index,
        query_embedding=jd_embedding,
        corpus=corpus,
        query_text=query_text,
        k=min(50, len(candidates))
    )
    
    # Map back to full candidate dictionaries
    retrieved_candidates = []
    for doc_id, fused_score in retrieved_tuples:
        cand = candidates[doc_id]
        cand["retrieval_fused_score"] = fused_score
        retrieved_candidates.append(cand)
        
    logger.info("Retrieved top %d candidates via hybrid search.", len(retrieved_candidates))

    # -------------------------------------------------------------------------
    # PHASE 3: 5-Signal Scoring
    # -------------------------------------------------------------------------
    logger.info("--- PHASE 3: 5-SIGNAL SCORING ---")
    
    for c in retrieved_candidates:
        s1 = semantic_fit_score(jd_embedding, c["resume_embedding"])
        s2 = skills_match_score(jd.get("required_skills", []), c.get("skills", []), adjacency_map)
        s3 = career_trajectory_score(c)
        s4 = behavioral_score(c)
        s5 = domain_alignment_score(jd.get("domain", ""), c.get("domains", []))
        
        scores = {
            "semantic": s1,
            "skills": s2,
            "trajectory": s3,
            "behavioral": s4,
            "domain": s5
        }
        
        c["composite_score"] = compute_final_score(scores)
        c["signal_breakdown"] = scores
        # Store individual score values in dict for LLM reference
        c["s1"] = s1
        c["s2"] = s2

    # Sort by composite score
    retrieved_candidates.sort(key=lambda x: x["composite_score"], reverse=True)
    top_20 = retrieved_candidates[:20]
    
    logger.info("Top candidate after Phase 3 mathematical scoring: %s (Score: %.4f)", 
                top_20[0].get("name") if top_20 else "N/A", 
                top_20[0].get("composite_score", 0.0) if top_20 else 0.0)

    # -------------------------------------------------------------------------
    # PHASE 4: Agentic Re-Rank
    # -------------------------------------------------------------------------
    logger.info("--- PHASE 4: AGENTIC RE-RANK ---")
    
    # Verify API key for LLM provider
    provider = args.provider.lower()
    api_key_env = "GROQ_API_KEY" if provider == "groq" else "GEMINI_API_KEY"
    api_key = os.getenv(api_key_env)
    
    if not api_key:
        logger.warning("%s not set. LLM Re-ranking will fall back to Phase 3 mathematical ranking.", api_key_env)
        # Force fallback ranking
        ranked_shortlist = [
            {
                "candidate_id": c.get("candidate_id") or c.get("id"),
                "rank": idx + 1,
                "rationale": f"Ranked by 5-signal composite score (semantic={c['s1']:.2f}, skills={c['s2']:.2f}). LLM API key not set."
            }
            for idx, c in enumerate(top_20)
        ]
    else:
        jd_summary = jd.get("summary", "")
        # Run agentic reranking
        ranked_shortlist = agentic_rerank(
            jd_summary=jd_summary,
            candidates=top_20,
            provider=provider
        )

    # -------------------------------------------------------------------------
    # Output Shortlist
    # -------------------------------------------------------------------------
    logger.info("Saving shortlist to: %s", args.output)
    save_shortlist_csv(ranked_shortlist, args.output, candidates)
    
    # -------------------------------------------------------------------------
    # (Optional) PHASE 5: Evaluation
    # -------------------------------------------------------------------------
    if args.eval:
        logger.info("--- PHASE 5: EVALUATION ---")
        metrics = evaluate_pipeline(ranked_shortlist, args.test_ground_truth)
        logger.info("=== EVALUATION METRICS ===")
        logger.info("  Precision@5: %.2f%%", metrics["precision@5"] * 100)
        logger.info("  NDCG@10:     %.4f", metrics["ndcg@10"])

    elapsed = time.time() - start_time
    logger.info("NexHire AI Pipeline complete in %.2f seconds.", elapsed)


if __name__ == "__main__":
    main()
