#!/usr/bin/env python3
"""
precompute.py — Run ONCE with network access before submission.
Extracts JD skills using Groq/Gemini and embeds the JD text.
"""
import os
import json
from docx import Document
from sentence_transformers import SentenceTransformer
import numpy as np
import re

# Simple .env parser to avoid strict external dependencies
def load_env():
    paths = [".env", "../nexhire-ai/.env", "nexhire-ai/.env", "../../nexhire-ai/.env"]
    for p in paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip().strip('"').strip("'")
            print(f"Loaded environment variables from {p}")
            return

def get_jd_text():
    doc = Document("job_description.docx")
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

def parse_jd_with_llm(jd_text):
    load_env()
    
    # Try Groq first
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        print("Using Groq API for JD parsing...")
        from groq import Groq
        client = Groq(api_key=groq_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "user",
                "content": f"""Parse this Job Description and return JSON only:
{{
  "core_skills": ["top 10-12 must-have technical skill names (e.g., Python, PyTorch, Vector Databases) - keep them short and standard"],
  "adjacent_skills": ["5-8 nice-to-have technical skill names (e.g., Docker, AWS) - keep them short and standard"],
  "domain_keywords": ["15 domain-specific industry terms"],
  "min_years_experience": 0,
  "seniority_level": "mid"
}}

JD: {jd_text}"""
            }],
            temperature=0.1
        )
        raw = response.choices[0].message.content
        clean = re.sub(r'```(?:json)?', '', raw).strip().strip('`')
        return json.loads(clean)
        
    # Try Gemini second
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        print("Using Gemini API for JD parsing...")
        import urllib.request
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
        prompt = f"""Parse this Job Description and return JSON only matching this schema:
{{
  "core_skills": ["top 10-12 must-have technical skill names (e.g., Python, PyTorch, Vector Databases) - keep them short and standard"],
  "adjacent_skills": ["5-8 nice-to-have technical skill names (e.g., Docker, AWS) - keep them short and standard"],
  "domain_keywords": ["15 domain-specific industry terms"],
  "min_years_experience": 0,
  "seniority_level": "mid"
}}

JD: {jd_text}"""
        
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            raw = res_data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(raw)

    raise ValueError("Neither GROQ_API_KEY nor GEMINI_API_KEY found in environment or .env files.")

VERIFIED_JD_SKILLS = {
    "core_skills": [
        "Python", "Embeddings", "Vector Databases", "Retrieval Systems", "Ranking Systems",
        "LLMs", "Fine-tuning", "Evaluation Frameworks", "NLP", "IR", "Hybrid Search"
    ],
    "adjacent_skills": [
        "Docker", "AWS", "LangChain", "OpenAI", "Pinecone", "Weaviate",
        "Qdrant", "Milvus", "OpenSearch", "Elasticsearch", "FAISS"
    ],
    "domain_keywords": [
        "AI", "ML", "NLP", "IR", "Recruiting Tech", "HR-tech", "Marketplace Products",
        "Distributed Systems", "Large-scale Inference Optimization", "Open-source Contributions",
        "Computer Vision", "Speech", "Robotics", "Closed-source Proprietary Systems",
        "Product Companies", "Consulting Firms", "Title-chasers", "Framework Enthusiasts"
    ],
    "min_years_experience": 5,
    "seniority_level": "mid"
}

def main():
    print("Reading job_description.docx...")
    jd_text = get_jd_text()
    
    verified_skills = VERIFIED_JD_SKILLS
    use_fallback = True
    
    print("Extracting skills and keywords via LLM...")
    try:
        jd_config = parse_jd_with_llm(jd_text)
        print("\n=== LLM-EXTRACTED SKILLS & KEYWORDS ===")
        print(json.dumps(jd_config, indent=2))
        print("=======================================\n")
        
        # Check if stdin is interactive (terminal) and ask for confirmation
        import sys
        if sys.stdin.isatty():
            try:
                ans = input("Use LLM-extracted skills? (y/n, default 'n' to use verified hardcoded skills): ").strip().lower()
                if ans == 'y':
                    use_fallback = False
                    verified_skills = jd_config
            except Exception:
                pass
    except Exception as e:
        print(f"Error parsing JD via LLM: {e}")
        print("Proceeding with verified fallback skills.")
        
    if use_fallback:
        print("\nUsing verified hardcoded skills:")
        print(json.dumps(verified_skills, indent=2))
        
    with open("jd_skills.json", "w", encoding="utf-8") as f:
        json.dump(verified_skills, f, indent=2)
    print("Saved jd_skills.json successfully!")

    print("Loading sentence-transformers model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    print("Generating local JD embedding...")
    emb = model.encode(jd_text)
    np.save("jd_embedding.npy", emb)
    print("Saved jd_embedding.npy successfully!")
    
    print("[DONE] Pre-computation complete!")

if __name__ == "__main__":
    main()
