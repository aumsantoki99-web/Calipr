#!/usr/bin/env python3
"""
Verdikt Ranker — Fully offline. No API calls. CPU only.
Usage: python rank.py --candidates candidates.jsonl --out submission.csv
"""
import os
import argparse
import json
import csv
import numpy as np
from datetime import date
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
import re
import time

# ── CONFIG ────────────────────────────────────────────────────────
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TOP_K_BM25 = 5000       # Pre-filter: BM25 top-5000 before embedding
TOP_K_FINAL = 100       # Output top 100

# Signal weights
W_SEMANTIC   = 0.30
W_SKILLS     = 0.25
W_CAREER     = 0.20
W_BEHAVIORAL = 0.15
W_DOMAIN     = 0.10

# JD-extracted values (from pre-computation step)
JD_CORE_SKILLS = []      # Filled by parse_jd()
JD_ADJACENT    = []
JD_DOMAIN_KW   = []
JD_MIN_EXP     = 0

SKILL_ADJACENCY = {
    "Python": ["Julia","R","Scala"],
    "PyTorch": ["TensorFlow","JAX","Keras","MXNet"],
    "React": ["Vue","Angular","Svelte","Next.js"],
    "FastAPI": ["Flask","Django","Express"],
    "PostgreSQL": ["MySQL","SQLite","MongoDB"],
    "Docker": ["Kubernetes","Podman"],
    "AWS": ["GCP","Azure","DigitalOcean"],
    "LangChain": ["LlamaIndex","Haystack","AutoGen"],
    "BERT": ["RoBERTa","DistilBERT","GPT-2","T5"],
    "YOLOv8": ["YOLOv5","Detectron2","EfficientDet"],
}

LEVEL_MAP = {
    "intern":0.10,"trainee":0.12,"junior":0.20,"associate":0.28,
    "mid":0.40,"engineer":0.40,"developer":0.40,"analyst":0.35,
    "senior":0.70,"lead":0.82,"staff":0.88,"principal":0.93,
    "architect":0.90,"director":0.93,"manager":0.72,"head":0.85,
    "vp":0.95,"cto":1.0,"founder":0.88
}

SIZE_MAP = {"1-10":1,"11-50":2,"51-200":3,"201-500":4,
            "501-1000":5,"1001-5000":6,"5001-10000":7,"10001+":8}

# ── TEXT UTILS ────────────────────────────────────────────────────
def build_candidate_text(c):
    p = c.get('profile', {})
    skills_text = " ".join([s.get('name','') for s in c.get('skills', [])])
    career_text = " ".join([jh.get('description','') for jh in c.get('career_history', [])])
    titles_text = " ".join([jh.get('title','') for jh in c.get('career_history', [])])
    return f"{p.get('summary','')} {p.get('headline','')} {p.get('current_title','')} {skills_text} {career_text} {titles_text}"

def tokenize(text):
    STOP = {"a","an","the","and","or","in","on","at","to","for","of","with","is","are","was","were","i","we","you"}
    return [t for t in re.findall(r'\b[a-z0-9][a-z0-9+#\.]*\b', text.lower()) if t not in STOP and len(t) > 1]

# ── SIGNALS ───────────────────────────────────────────────────────
def sig_semantic(emb_candidate, emb_jd):
    dot = np.dot(emb_candidate, emb_jd)
    norms = np.linalg.norm(emb_candidate) * np.linalg.norm(emb_jd)
    return float(dot / norms) if norms > 0 else 0.0

def sig_skills(candidate_skills, assessment_scores):
    if not JD_CORE_SKILLS:
        return 0.5
    PROF = {'beginner':0.4,'intermediate':0.6,'advanced':0.85,'expert':1.0}
    cand_map = {s.get('name','').lower(): s for s in candidate_skills}
    score = 0.0
    for jd_skill in JD_CORE_SKILLS:
        jl = jd_skill.lower()
        if jl in cand_map:
            s = cand_map[jl]
            base = PROF.get(s.get('proficiency','intermediate'), 0.6)
            dur  = min(s.get('duration_months',0)/24, 1.0) * 0.15
            asmnt= (assessment_scores.get(jd_skill, 0)/100) * 0.10
            score += min(base + dur + asmnt, 1.0)
        else:
            adj_list = SKILL_ADJACENCY.get(jd_skill, [])
            if any(a.lower() in cand_map for a in adj_list):
                score += 0.40
    return min(score / max(len(JD_CORE_SKILLS), 1), 1.0)

def sig_career(c):
    p = c.get('profile', {})
    career = c.get('career_history', [])
    edu = c.get('education', [])
    title = p.get('current_title','').lower()
    seniority = next((v for k,v in LEVEL_MAP.items() if k in title), 0.35)
    sizes = [SIZE_MAP.get(jh.get('company_size','1-10'), 1) for jh in career]
    prog = max((sizes[-1]-sizes[0])/7, 0.0) if len(sizes) > 1 else 0.0
    tier_bonus = {'tier_1':0.15,'tier_2':0.10,'tier_3':0.05,'tier_4':0.0,'unknown':0.02}
    best_tier = max((tier_bonus.get(e.get('tier','unknown'),0.02) for e in edu), default=0.02)
    return min(seniority*0.50 + prog*0.30 + best_tier*0.20, 1.0)

def sig_behavioral(rs):
    try:
        last_active = date.fromisoformat(rs.get('last_active_date', '').split('T')[0])
        days_ago = (date.today() - last_active).days
    except Exception:
        days_ago = 30
    freshness  = max(0.0, 1.0 - days_ago/90)
    completeness = rs.get('profile_completeness_score', 80)/100
    response_rate = rs.get('recruiter_response_rate', 0.5)
    resp_time  = max(0, 1 - rs.get('avg_response_time_hours', 24)/72)
    interview  = rs.get('interview_completion_rate', 0.5)
    engagement = response_rate*0.4 + resp_time*0.3 + interview*0.3
    gh = rs.get('github_activity_score', -1)
    github = 0.3 if gh == -1 else gh/100
    offer = rs.get('offer_acceptance_rate', -1)
    offer_n = 0.5 if offer == -1 else max(offer, 0)
    otw = 1.0 if rs.get('open_to_work_flag', False) else 0.3
    verified = (int(rs.get('verified_email', False)) + int(rs.get('verified_phone', False)) + int(rs.get('linkedin_connected', False)))/3
    saved = min(rs.get('saved_by_recruiters_30d', 0)/10, 1.0)
    return min(
        completeness*0.18 + freshness*0.15 + engagement*0.25 +
        github*0.15 + offer_n*0.10 + otw*0.05 + verified*0.07 + saved*0.05, 1.0
    )

def sig_domain(c):
    if not JD_DOMAIN_KW:
        return 0.5
    p = c.get('profile', {})
    industries = [p.get('current_industry','')] + [jh.get('industry','') for jh in c.get('career_history',[])]
    text = (p.get('summary','') + ' ' + p.get('headline','') + ' ' + ' '.join(industries)).lower()
    hits = sum(1 for kw in JD_DOMAIN_KW if kw.lower() in text)
    return min(hits / max(len(JD_DOMAIN_KW), 1), 1.0)

def compute_score(c, emb_c, emb_jd):
    rs = c.get('redrob_signals', {})
    s1 = sig_semantic(emb_c, emb_jd)
    s2 = sig_skills(c.get('skills',[]), rs.get('skill_assessment_scores',{}))
    s3 = sig_career(c)
    s4 = sig_behavioral(rs)
    s5 = sig_domain(c)
    final = s1*W_SEMANTIC + s2*W_SKILLS + s3*W_CAREER + s4*W_BEHAVIORAL + s5*W_DOMAIN
    return round(final, 4), s1, s2, s3, s4, s5

def generate_reasoning(c, s2_skills):
    p = c.get('profile', {})
    rs = c.get('redrob_signals', {})
    matched = round(s2_skills * max(len(JD_CORE_SKILLS), 1))
    return (f"{p.get('current_title', 'Developer')} with {p.get('years_of_experience', 0)} yrs; "
            f"{matched} core skills matched; "
            f"response rate {rs.get('recruiter_response_rate', 0.0):.2f}.")

# ── MAIN PIPELINE ─────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    
    t0 = time.time()
    print("Loading model...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    
    # Load JD (pre-computed or from docx)
    print("Loading JD embedding...")
    try:
        emb_jd = np.load("jd_embedding.npy")
    except FileNotFoundError:
        from docx import Document
        doc = Document("job_description.docx")
        jd_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        emb_jd = model.encode(jd_text)
        np.save("jd_embedding.npy", emb_jd)
    
    # Load JD skills (from jd_skills.json if exists)
    try:
        with open("jd_skills.json", encoding="utf-8") as f:
            jd_config = json.load(f)
            JD_CORE_SKILLS.extend(jd_config.get("core_skills", []))
            JD_ADJACENT.extend(jd_config.get("adjacent_skills", []))
            JD_DOMAIN_KW.extend(jd_config.get("domain_keywords", []))
    except FileNotFoundError:
        print("[WARN] jd_skills.json not found. Skills scoring will be approximate.")
    
    # ── PHASE 1: BM25 Pre-filter ────────────────────────────────
    print("Phase 1: BM25 pre-filter...")
    candidates_raw = []
    corpus_tokens  = []
    jd_query = tokenize(" ".join(JD_CORE_SKILLS + JD_DOMAIN_KW))
    
    with open(args.candidates, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            c = json.loads(line)
            candidates_raw.append(c)
            corpus_tokens.append(tokenize(build_candidate_text(c)))
    
    print(f"  Loaded {len(candidates_raw):,} candidates")
    
    if jd_query and len(corpus_tokens) > 0:
        bm25 = BM25Okapi(corpus_tokens)
        bm25_scores = bm25.get_scores(jd_query)
        top_indices = np.argsort(bm25_scores)[-TOP_K_BM25:][::-1]
        candidates_filtered = [candidates_raw[i] for i in top_indices]
    else:
        candidates_filtered = candidates_raw[:TOP_K_BM25]
    
    print(f"  After BM25 filter: {len(candidates_filtered):,} candidates")
    
    # ── PHASE 2: Embed + Score ──────────────────────────────────
    print("Phase 2: Embedding + scoring...")
    texts = [build_candidate_text(c) for c in candidates_filtered]
    embeddings = model.encode(texts, batch_size=256, show_progress_bar=True)
    
    scored = []
    for i, c in enumerate(candidates_filtered):
        final, s1, s2, s3, s4, s5 = compute_score(c, embeddings[i], emb_jd)
        scored.append({
            "candidate_id": c["candidate_id"],
            "score": final,
            "s2": s2,
            "reasoning": generate_reasoning(c, s2),
            "_c": c
        })
    
    # ── PHASE 3: Sort + Top 100 ─────────────────────────────────
    scored.sort(key=lambda x: (-x["score"], x["candidate_id"]))
    top100 = scored[:TOP_K_FINAL]
    
    # Create output directory if it doesn't exist
    out_dir = os.path.dirname(args.out)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
        
    # ── PHASE 4: Write CSV ──────────────────────────────────────
    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        for rank, row in enumerate(top100, 1):
            # Format score to 4 decimal places matching requirements
            writer.writerow([row["candidate_id"], rank, f"{row['score']:.4f}", row["reasoning"]])
    
    elapsed = round(time.time() - t0, 1)
    print(f"\n[DONE] Done in {elapsed}s -> {args.out}")
    print(f"Top 3: {[(r['candidate_id'], f'{r['score']:.4f}') for r in top100[:3]]}")

if __name__ == "__main__":
    main()
