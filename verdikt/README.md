# Verdikt Offline Ranker — Redrob Intelligent Candidate Discovery

The **Verdikt Offline Ranker** is a premium, CPU-optimized, and fully offline candidates ranking pipeline built for the Redrob Intelligent Candidate Discovery & Ranking Challenge. It is designed to run in under 5 minutes on standard CPUs, using under 180MB of RAM, and produces a valid submission file compliant with all challenge criteria.

---

## Architecture Overview

The pipeline leverages a hybrid sparse-dense retrieval model combined with five multi-dimensional scoring signals:

```
  [Candidates Dataset] (106K jsonl stream)
          │
          ▼
┌───────────────────┐
│ Title Pre-filter  │  ◄── Drops non-tech roles & irrelevant engineering fields
└─────────┬─────────┘      (Sparing candidates with proven ML/tech skill profiles)
          │ (65K candidates)
          ▼
┌───────────────────┐
│    BM25 Sparse    │  ◄── Tokenized search query strictly using JD Core Skills
└─────────┬─────────┘
          │ (Top 8,000 recall candidates)
          ▼
┌───────────────────┐
│ Dense Embeddings  │  ◄── CPU Batch encoding using Sentence Transformers (all-MiniLM-L6-v2)
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  5-Signal Fusion  │  ◄── Semantic, Skills, Career, Behavioral, and Domain scores
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│   Post-Filters    │  ◄── Open-To-Work multiplier (0.75x) + Explicit Tie-Breakers
└─────────┬─────────┘
          │
          ▼
    [Top 100 Output]  (submission.csv)
```

---

## Pipeline Signals & Weights

### 1. Semantic Match (30% Weight)
* **Formula**: Cosine similarity between candidate text representation (summary + current title + skills + career history) and the JD embedding.
* **Model**: Local `all-MiniLM-L6-v2` encoder (no API calls).

### 2. Core Skills Match (25% Weight)
* **Proficiency Scaling**: Beginners start at `0.4`, experts at `1.0`.
* **Verified Override**: Candidates scoring $\ge 70$ in a core skill assessment are auto-overridden to `expert` (`1.0`).
* **Adjacent Penalty**: If a core skill is absent, searches for custom skill adjacency mappings (e.g., Python $\rightarrow$ R, PyTorch $\rightarrow$ TensorFlow) at a `0.40` default rate.

### 3. Career Trajectory (20% Weight)
* **Seniority Map**: Titles mapped to hierarchical weights (CTO: `1.0`, Intern: `0.1`).
* **Company Progression**: Progression bonus for growth across past companies.
* **Education Tier**: Graduation tier bonus (Tier-1: `+0.15`, Tier-2: `+0.10`).
* **Consulting Firm Penalty**: A `0.85` career trajectory multiplier applies if the candidate's current company is a service consulting firm (TCS, Infosys, Wipro, Accenture, etc.).

### 4. Behavioral Engagement (15% Weight)
Includes detailed internal weight distributions:
* **Profile Completeness**: `18%`
* **Profile Freshness**: `12%` (sliding scale based on `last_active_date` up to 90 days)
* **Engagement Composite**: `25%` (comprising average response time, response rate, and interview completion rate)
* **GitHub Activity**: `15%`
* **Offer Acceptance**: `10%`
* **Notice Period**: `10%` (score scaled as `max(0.0, 1.0 - (notice_period / 180))`)
* **Open to Work (Internal)**: `5%`
* **Verification Score**: `5%` (combines email, phone, and LinkedIn connections)
* **Relocation Bonus**: Adds a flat `+0.05` bonus if `willing_to_relocate == True` or `preferred_work_mode == "remote"`.

### 5. Domain Alignment (10% Weight)
* Matches candidate's industry background keywords against target business sectors (AI, Recruiting Tech, SaaS, Marketplace, etc.).

### Post-Scoring Adjustments
* **Availability Multiplier**: A post-fusion multiplier of `0.75x` is applied if `open_to_work_flag` is `False`.
* **Tie-Breaker**: Scores are sorted descending; ties are explicitly broken by `candidate_id` in lexicographical ascending order.

---

## Resource Requirements & Execution

* **RAM Footprint**: ~170MB (achieved by streaming the candidate dataset line-by-line and tokenizing only the required subset in memory).
* **Execution Time**: ~5 minutes on CPU.

### Step 1: Pre-computation (Run Once)
Extracts key terms from the job description and generates the JD embedding.
```bash
python precompute.py
```
*(If LLM access is unconfigured, it safely defaults to the hardcoded, verified JD skills config).*

### Step 2: Rank Candidates
Runs the pipeline offline on the dataset.
```bash
python rank.py --candidates candidates.jsonl --out outputs/submission.csv
```

### Step 3: Validate Outputs
Verify that the output is formatted correctly and satisfies the challenge rules.
```bash
python validate_submission.py outputs/submission.csv
```
