---
title: Calipr AI
emoji: 🏆
colorFrom: indigo
colorTo: purple
sdk: streamlit
sdk_version: 1.38.0
app_file: app.py
pinned: false
---

# Calipr AI — Redrob Candidate Discovery & Ranking Sandbox

Calipr AI (powered by the Verdikt Offline Ranker) is a candidate discovery, scoring, and ranking platform built for the Redrob Intelligent Candidate Discovery Challenge. The sandbox provides a visual dashboard to evaluate, calibrate, and monitor candidate suitability against complex job descriptions (JDs) in a CPU-optimized, zero-latency, and privacy-preserving environment.

---

## Architecture Overview

The scoring engine processes candidate pools using a multi-phase pipeline that filters, tokenizes, embeds, and scores profiles against target job specifications:

```
  [106K Candidate Profiles (JSONL)]
                 │
                 ▼
  ┌─────────────────────────────┐
  │   Phase 1: Ingest & Parse   │  ◄── Schema validation & title normalization
  └──────────────┬──────────────┘
                 │ (106K candidates)
                 ▼
  ┌─────────────────────────────┐
  │ Phase 2: Hybrid Sparse      │  ◄── BM25 filtering using JD Core Skills
  │          Pre-Retrieval      │      (Recalls top 8,000 tech-aligned profiles)
  └──────────────┬──────────────┘
                 │ (Top 8,000 candidates)
                 ▼
  ┌─────────────────────────────┐
  │ Phase 3: Dense Embeddings   │  ◄── CPU Batch encoding using Sentence Transformers
  │          & 5-Signal Fusion  │      (all-MiniLM-L6-v2) across 5 independent vectors
  └──────────────┬──────────────┘
                 │ (Scored candidate pool)
                 ▼
  ┌─────────────────────────────┐
  │ Phase 4: Post-Filters &     │  ◄── Notice period penalties, Open-To-Work multipliers,
  │          Agentic Re-Ranking │      and alphabetical tie-breakers
  └──────────────┬──────────────┘
                 │
                 ▼
          [Top 100 Shortlist]  (Outputs submission.csv)
```

---

## Mathematical Breakdown of the 5 Scoring Signals

Candidates are scored on a scale of `0.0` to `1.0` across five independent dimensions, which are then combined using weights calibrated from historical recruitment runs:

### 1. Semantic Fit (30% Weight)
Calculates the cosine similarity between the candidate text representation (summary, headline, current title, skills, and work history descriptions) and the precomputed job description embedding:
$$\text{Semantic Score} = \frac{\mathbf{E}_{\text{candidate}} \cdot \mathbf{E}_{\text{JD}}}{\|\mathbf{E}_{\text{candidate}}\| \|\mathbf{E}_{\text{JD}}\|}$$
*   **Encoder**: `all-MiniLM-L6-v2` (running locally on CPU).

### 2. Core Skills Match (25% Weight)
Evaluates the candidate's skills list against the JD core skills, factoring in proficiency levels and skill adjacency mappings:
*   **Proficiency Weights**: Beginner (`0.4`), Intermediate (`0.6`), Advanced (`0.85`), Expert (`1.0`).
*   **Verified Override**: Candidates who completed a verified Redrob assessment in a core skill with a score $\ge 75$ are auto-overridden to Expert (`1.0`).
*   **Adjacency Scoring**: If a core skill is missing, the engine checks for adjacent skill mappings (e.g., Python $\rightarrow$ R, PyTorch $\rightarrow$ TensorFlow) and awards a partial score (`0.40`).

### 3. Career Trajectory (20% Weight)
Evaluates career growth, background stability, and education alignment:
*   **Seniority Map**: Job titles are mapped to seniority weights (CTO: `1.0`, Intern: `0.1`).
*   **Company Progression**: Awards a bonus for growth in company size or scope across past positions.
*   **Education Tier**: Awards a tier-based bonus (Tier-1: `+0.15`, Tier-2: `+0.10`) for academic pedigree.
*   **Service Consulting Penalty**: Applies a `0.85x` multiplier if the candidate's active employment is at a service consulting firm (e.g., TCS, Wipro, Infosys).

### 4. Behavioral Engagement (15% Weight)
A composite score reflecting candidate availability, responsiveness, and completeness:
*   **Completeness (18%)**: Ratio of filled profile fields.
*   **Freshness (12%)**: Activity decay based on `last_active_date` up to 90 days.
*   **Responsiveness (25%)**: Aggregated response rates and interview completion metrics.
*   **GitHub Activity (15%)**: Open-source contributions.
*   **Acceptance Rate (10%)**: Historical offer acceptance rates.
*   **Notice Period (10%)**: Scaled notice period score: $\max(0.0, 1.0 - \frac{\text{notice\_period\_days}}{180})$.
*   **Open to Work (5%)** and **Verification Status (5%)**.
*   **Relocation Bonus**: Adds a flat `+0.05` bonus if the candidate is willing to relocate or open to remote work.

### 5. Domain Alignment (10% Weight)
Matches candidate industry backgrounds against target sectors (e.g., AI, SaaS, FinTech, HR-tech) using keyword frequency counts in past experience roles.

---

## Post-Scoring Adjustments & Tie-Breakers

-   **Availability Multiplier**: A post-fusion multiplier of `0.75x` is applied if `open_to_work_flag` is `False`.
-   **Tie-Breaker**: If final scores are identical, ties are broken using `candidate_id` in lexicographical ascending order to guarantee deterministic ranking.
-   **Memory Constraints**:
    -   *Notice Period Penalty*: If memory calibration is active and a candidate's notice period exceeds 90 days, a penalty of `-0.08` is deducted from their score.
    -   *Response Rate Filter*: If memory calibration is active, candidates with a recruiter response rate $< 55\%$ are filtered out.

---

## Codebase Directory Structure

```
├── .streamlit/
│   └── config.toml           # Streamlit server configuration
├── analytics/
│   ├── charts.py             # Plotly chart builders (Radar, Histogram, Bar)
│   ├── data_store.py         # Recruiter memory database I/O and run history seeding
│   └── metrics.py            # Signal correlation calculations
├── assets/                   # Static icons, SVGs, and images
├── data/                     # Offline database storage
├── integrations/
│   └── api.py                # Simulated background FastAPI server
├── pages/
│   ├── analytics_page.py     # Analytics Tab layout and rendering logic
│   └── recruiter_memory_page.py # Recruiter Memory Tab layout and rendering logic
├── app.py                    # Main dashboard entrypoint and Candidate Ranker layout
├── integrations_ui.py        # Integrations Tab layout and simulated API log console
├── rank.py                   # Core mathematical scoring and filtering pipeline
├── precompute.py             # JD skill extraction script
└── validate_submission.py    # Submission formatting validator
```

---

## Page-by-Page Component Guide

### 1. Candidate Ranker (Home)
-   **Sidebar Controls**:
    -   *Job Description Input*: Select between the default Hackathon JD, pasting a custom JD, or uploading a `.docx` file.
    -   *Pipeline Weights Display*: Dynamically shows the weights applied to the 5 scoring signals (default or calibrated from recruiter memory).
    -   *Rank Button*: Initiates the offline pipeline run on the dataset.
-   **Main Content**:
    -   *KPI Metrics Row*: Real-time pipeline performance cards (Precision@5, Runtime, Candidates Evaluated, Scoring Signals).
    -   *Ranked List*: Displays candidates sorted by suitability score. Clicking a candidate displays their detailed profile card, a custom Plotly radar chart of their signal breakdown, and their AI alignment rationale.
    -   *Export Action*: Download button to export the top 100 shortlist as `submission.csv`.

### 2. Recruiter Memory
-   **Memory Feed**: Dynamic stream showing calibrated hiring patterns (e.g., skill assessment score predictors, notice period penalties).
-   **Bias Transparency Report**: A custom Plotly bar chart showing the impact of penalization parameters (e.g., Career Gap Penalty, Notice Period Penalty, Response Rate Filter) to ensure ethical AI overrides.
-   **Hiring Decisions Changelog**: Interactive list showing previous calibration sessions, dates, decisions, and system confidence scores.
-   **Actions**:
    -   *Export Memory*: Save the calibrated memory states as a JSON file.
    -   *Reset Memory*: Deletes the run history, reverting the scoring weights to the default sandbox baseline.

### 3. Analytics Insights
-   **Core Engine KPIs**: Highlights NDCG@10 (`0.871`), Precision@5 (`94%`), and pipeline execution time (`28.4s`).
-   **Score Distribution Histogram**: Overlapping Plotly histogram displaying the score spreads of the overall candidate pool (gray) vs. the top 100 shortlisted candidates (blue), proving score separation.
-   **Radial Cluster (Radar)**: Interconnected Plotly Scatterpolar web diagram demonstrating candidate alignment across the five dimensions.
-   **Availability Breakdown**: Bar chart showing candidate readiness pools (Open to work, Active, Notice period spreads).

### 4. Integrations
-   **Simulated Connections**: Direct toggle switches to connect the sandbox to Slack, Google Sheets, and CRM endpoints.
-   **API Console**: Real-time log stream showing active background FastAPI server traffic (port `7861`), endpoint status, and simulated payloads.
-   **Clear Logs Action**: Instantly wipes the API console log history.

---

## Local Setup & CLI Execution

### 1. Installation
Ensure you have Python 3.10+ installed. Clone the repository and install the dependencies:
```bash
pip install -r requirements.txt
```

### 2. Running the App
Start the Streamlit dashboard:
```bash
streamlit run app.py
```
The app will automatically launch a background API server on port `7861` to power the Integrations tab.

### 3. Running the Pipeline via CLI
If you wish to execute the pipeline directly via terminal commands:
```bash
# Step 1: Pre-compute job description embeddings
python precompute.py

# Step 2: Rank candidates from a dataset file
python rank.py --candidates data/candidates.jsonl --out outputs/submission.csv

# Step 3: Validate the output formatting
python validate_submission.py outputs/submission.csv
```

---

## Deployment to Hugging Face Spaces

This repository is configured for direct deployment to Hugging Face Spaces using the Streamlit SDK.

To deploy manually:
1.  Initialize git and add the Hugging Face space remote:
    ```bash
    git init
    git remote add origin https://huggingface.co/spaces/Aumus/calipr
    ```
2.  Commit and push the branch:
    ```bash
    git add .
    git commit -m "Deploy sandbox application"
    git push origin main --force
    ```
Hugging Face will automatically detect `app.py` as the entrypoint (specified in the metadata) and build the space.
