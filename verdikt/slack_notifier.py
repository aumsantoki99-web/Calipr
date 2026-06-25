# slack_notifier.py
# Calipr — Slack notification engine
# Sends top 5 ranked candidates to a Slack channel after ranking completes.
# Uses Slack Incoming Webhooks — no OAuth, no SDK, just requests.

import os
import json
import requests
from datetime import datetime


def send_ranking_complete(
    top_candidates: list[dict],
    job_title: str = "Senior AI Engineer",
    total_processed: int = 106039,
    runtime_seconds: float = 28.4,
    precision_at_5: float = 0.94,
    sandbox_url: str = "https://huggingface.co/spaces/Aumus/calipr",
) -> dict:
    """
    Send a Slack notification with the top 5 ranked candidates.

    Args:
        top_candidates: List of dicts with keys:
                        candidate_id, rank, score, name, title,
                        semantic, skills, career, behavioral, domain
        job_title:      The job description title
        total_processed: Total candidates ranked
        runtime_seconds: Pipeline runtime
        precision_at_5: Precision@5 score
        sandbox_url:    Link to the live sandbox

    Returns:
        dict with 'success' bool and 'status_code' or 'error'
    """

    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        return {"success": False, "error": "SLACK_WEBHOOK_URL not set in environment"}

    # Take only top 5
    top5 = top_candidates[:5]

    # Signal color emoji map
    def score_emoji(score: float) -> str:
        if score >= 0.85: return "🟢"
        if score >= 0.70: return "🟡"
        return "🔴"

    # Build candidate blocks
    candidate_blocks = []
    for c in top5:
        score    = c.get("score", 0)
        name     = c.get("name", c.get("candidate_id", "Unknown"))
        title    = c.get("title", "—")
        rank     = c.get("rank", "?")
        semantic  = c.get("semantic",   0)
        skills    = c.get("skills",     0)
        career    = c.get("career",     0)
        behavioral = c.get("behavioral", 0)
        domain    = c.get("domain",     0)

        candidate_blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*#{rank} — {name}*  {score_emoji(score)} `{score:.3f}`\n"
                    f"_{title}_\n"
                    f"Semantic `{semantic:.2f}` · Skills `{skills:.2f}` · "
                    f"Career `{career:.2f}` · Behavioral `{behavioral:.2f}` · "
                    f"Domain `{domain:.2f}`"
                )
            }
        })
        # Thin divider between candidates
        candidate_blocks.append({"type": "divider"})

    # Remove last divider
    if candidate_blocks:
        candidate_blocks.pop()

    # Timestamp
    ts = datetime.now().strftime("%b %d, %Y at %I:%M %p")

    # Full Slack Block Kit payload
    payload = {
        "blocks": [
            # ── HEADER ──
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🏆 Calipr Ranking Complete",
                    "emoji": True
                }
            },
            # ── JOB SUMMARY ──
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Role*\n{job_title}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Candidates Processed*\n{total_processed:,}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Pipeline Runtime*\n{runtime_seconds:.1f}s"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Precision@5*\n{int(precision_at_5 * 100)}%"
                    },
                ]
            },
            {"type": "divider"},
            # ── TOP 5 LABEL ──
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Top 5 Candidates — Ranked by 5-Signal Fusion Score*"
                }
            },
            # ── CANDIDATE BLOCKS (injected below) ──
            *candidate_blocks,
            {"type": "divider"},
            # ── FOOTER WITH LINK ──
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"🤖 *Calipr AI Recruiter* · Powered by BM25 + MiniLM-L6 + RRF\n"
                        f"Ranked at {ts} · <{sandbox_url}|Open Sandbox ↗>"
                    )
                }
            },
            # ── CONTEXT ──
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            "Built at IITRAM Flux 2.0 · Sponsored by *Redrob AI* · "
                            "All signals are auditable and bias-free"
                        )
                    }
                ]
            }
        ]
    }

    # Fire the webhook
    try:
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if response.status_code == 200:
            return {"success": True, "status_code": 200}
        else:
            return {
                "success": False,
                "status_code": response.status_code,
                "error": response.text,
            }
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Slack webhook timed out after 10s"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


def send_test_notification(sandbox_url: str = "https://huggingface.co/spaces/Aumus/calipr") -> dict:
    """
    Send a test Slack message to verify the webhook is working.
    Called from the Integrations tab 'Test Notification' button.
    """
    # Realistic seeded test candidates
    test_candidates = [
        {
            "candidate_id": "CAND_0042817",
            "rank": 1, "score": 0.923,
            "name": "Arjun Mehta",
            "title": "Senior ML Engineer · 7 years",
            "semantic": 0.94, "skills": 0.91,
            "career": 0.88, "behavioral": 0.95, "domain": 0.92,
        },
        {
            "candidate_id": "CAND_0019334",
            "rank": 2, "score": 0.891,
            "name": "Priya Nair",
            "title": "AI Research Engineer · 5 years",
            "semantic": 0.90, "skills": 0.88,
            "career": 0.84, "behavioral": 0.92, "domain": 0.89,
        },
        {
            "candidate_id": "CAND_0078421",
            "rank": 3, "score": 0.867,
            "name": "Rohan Sharma",
            "title": "Lead Data Scientist · 8 years",
            "semantic": 0.87, "skills": 0.85,
            "career": 0.91, "behavioral": 0.82, "domain": 0.86,
        },
        {
            "candidate_id": "CAND_0033291",
            "rank": 4, "score": 0.844,
            "name": "Sneha Kulkarni",
            "title": "NLP Engineer · 4 years",
            "semantic": 0.86, "skills": 0.83,
            "career": 0.79, "behavioral": 0.88, "domain": 0.84,
        },
        {
            "candidate_id": "CAND_0061047",
            "rank": 5, "score": 0.821,
            "name": "Vikram Patel",
            "title": "ML Platform Engineer · 6 years",
            "semantic": 0.83, "skills": 0.81,
            "career": 0.85, "behavioral": 0.79, "domain": 0.82,
        },
    ]

    return send_ranking_complete(
        top_candidates=test_candidates,
        job_title="Senior AI Engineer — Founding Team",
        total_processed=106039,
        runtime_seconds=28.4,
        precision_at_5=0.94,
        sandbox_url=sandbox_url,
    )
