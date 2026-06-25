import requests
from datetime import datetime
from integrations.config import SLACK_WEBHOOK_URL
from integrations.activity_log import log_activity

def send_ranking_notification(ranked_candidates, job_title="Senior AI Engineer",
                               runtime_seconds=0.0, top_n=5):
    if not SLACK_WEBHOOK_URL:
        return {"success": False, "message": "SLACK_WEBHOOK_URL not configured."}

    top    = ranked_candidates[:top_n]
    medal  = ["🥇","🥈","🥉","4️⃣","5️⃣"]
    blocks = [
        {"type":"header","text":{"type":"plain_text","text":"🏆 Calipr AI — Ranking Complete","emoji":True}},
        {"type":"section","fields":[
            {"type":"mrkdwn","text":f"*Role:*\n{job_title}"},
            {"type":"mrkdwn","text":f"*Runtime:*\n{runtime_seconds:.1f}s"},
            {"type":"mrkdwn","text":f"*Total Ranked:*\n{len(ranked_candidates):,}"},
            {"type":"mrkdwn","text":f"*Shortlist:*\n{top_n} candidates"}
        ]},
        {"type":"divider"},
        {"type":"section","text":{"type":"mrkdwn","text":f"*Top {top_n} Candidates:*"}}
    ]

    for i, c in enumerate(top):
        score     = c.get("score", c.get("final_score", 0))
        name      = c.get("name", c.get("candidate_id", "Unknown"))
        title     = c.get("current_title","")
        years     = c.get("years_of_experience", c.get("years_experience", 0))
        reasoning = c.get("reasoning", c.get("ai_recruiter_rationale",""))
        sem       = "🟢" if score >= 0.75 else "🟡" if score >= 0.5 else "🔴"
        short_r   = reasoning[:120] + "..." if len(reasoning) > 120 else reasoning

        blocks.append({"type":"section","text":{"type":"mrkdwn","text":
            f"{medal[i]} *#{i+1} {name}*\n_{title} · {years:.1f} yrs_\n{sem} Score: *{score:.3f}*\n_{short_r}_"
        }})

    blocks += [
        {"type":"divider"},
        {"type":"context","elements":[{"type":"mrkdwn",
            "text":f"📊 Calipr AI · {datetime.now().strftime('%d %b %Y, %I:%M %p')}"}]}
    ]

    try:
        r = requests.post(SLACK_WEBHOOK_URL,
                          json={"text":f"🏆 Calipr ranked {len(ranked_candidates):,} for {job_title}",
                                "blocks":blocks},
                          timeout=10)
        if r.status_code == 200 and r.text == "ok":
            log_activity("Slack","💬",f"Sent top {top_n} candidates for *{job_title}* to #recruiting","success")
            return {"success":True,"message":f"Top {top_n} candidates sent to Slack."}
        return {"success":False,"message":f"Slack returned {r.status_code}: {r.text}"}
    except Exception as e:
        return {"success":False,"message":str(e)}

def send_test_notification():
    if not SLACK_WEBHOOK_URL:
        return {"success":False,"message":"SLACK_WEBHOOK_URL not set."}
    try:
        r = requests.post(SLACK_WEBHOOK_URL,
                          json={"text":"✅ Calipr AI — Slack integration working!",
                                "blocks":[{"type":"section","text":{"type":"mrkdwn",
                                "text":"🏆 *Calipr AI* — Test successful!\nYou'll receive shortlists here after each run.\n_aumus-calipr.hf.space_"}}]},
                          timeout=8)
        if r.status_code == 200:
            return {"success":True,"message":"Test message sent to Slack ✓"}
        return {"success":False,"message":f"Error {r.status_code}: {r.text}"}
    except Exception as e:
        return {"success":False,"message":str(e)}
