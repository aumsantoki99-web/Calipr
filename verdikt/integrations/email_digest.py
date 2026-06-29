from datetime import datetime
from integrations.config import SENDGRID_API_KEY, RECRUITER_EMAIL
from integrations.activity_log import log_activity

def build_email_html(ranked_candidates, job_title, runtime):
    top10 = ranked_candidates[:10]
    rows  = ""
    for c in top10:
        score = c.get("score", c.get("final_score",0))
        name  = c.get("name", c.get("candidate_id","Unknown"))
        title = c.get("current_title","")
        years = c.get("years_of_experience", c.get("years_experience",0))
        r     = c.get("reasoning", c.get("ai_recruiter_rationale",""))
        rank  = c.get("rank","")
        color = "#2563EB" if score>=0.75 else "#0A0A0A" if score>=0.5 else "#E5E7EB"
        rows += f"""<tr style="border-bottom:1px solid #F3F4F6;">
            <td style="padding:12px 16px;font-weight:700;color:#6B7280;font-size:13px;">#{rank}</td>
            <td style="padding:12px 16px;">
                <div style="font-weight:700;color:#0A0A0A;font-size:14px;">{name}</div>
                <div style="color:#9CA3AF;font-size:12px;">{title} · {years:.1f} yrs</div>
            </td>
            <td style="padding:12px 16px;font-size:18px;font-weight:800;
                       color:{color};font-family:monospace;">{score:.3f}</td>
            <td style="padding:12px 16px;color:#6B7280;font-size:12px;
                       line-height:1.5;">{r[:140]}</td>
        </tr>"""

    return f"""<!DOCTYPE html><html><body style="margin:0;background:#F8FAFC;
font-family:Inter,-apple-system,sans-serif;">
<div style="max-width:680px;margin:40px auto;background:#fff;
            border-radius:16px;overflow:hidden;box-shadow:0 4px 40px rgba(0,0,0,.08);">
  <div style="background:#0A0A0A;padding:28px 36px;">
    <div style="font-size:20px;font-weight:800;color:#fff;letter-spacing:-.04em;">Calipr AI</div>
    <div style="font-size:13px;color:#6B7280;margin-top:3px;">Candidate Ranking Report</div>
  </div>
  <div style="padding:24px 36px;">
    <div style="font-size:13px;color:#9CA3AF;margin-bottom:4px;text-transform:uppercase;
                letter-spacing:.08em;font-weight:700;">ROLE</div>
    <div style="font-size:20px;font-weight:700;color:#0A0A0A;">{job_title}</div>
    <div style="font-size:12px;color:#9CA3AF;margin-top:4px;">
        {len(ranked_candidates):,} candidates · {runtime:.1f}s · {datetime.now().strftime('%d %b %Y')}</div>
  </div>
  <div style="padding:0 36px 28px;">
    <table style="width:100%;border-collapse:collapse;border:1px solid #E5E7EB;border-radius:10px;overflow:hidden;">
      <thead><tr style="background:#F8FAFC;">
        <th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;
                   text-transform:uppercase;letter-spacing:.08em;color:#9CA3AF;
                   border-bottom:1px solid #E5E7EB;">#</th>
        <th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;
                   text-transform:uppercase;letter-spacing:.08em;color:#9CA3AF;
                   border-bottom:1px solid #E5E7EB;">Candidate</th>
        <th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;
                   text-transform:uppercase;letter-spacing:.08em;color:#9CA3AF;
                   border-bottom:1px solid #E5E7EB;">Score</th>
        <th style="padding:10px 16px;text-align:left;font-size:10px;font-weight:700;
                   text-transform:uppercase;letter-spacing:.08em;color:#9CA3AF;
                   border-bottom:1px solid #E5E7EB;">AI Rationale</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
  <div style="padding:0 36px 28px;text-align:center;">
    <a href="https://aumus-calipr.hf.space" style="display:inline-block;
       background:#0A0A0A;color:#fff;text-decoration:none;padding:13px 28px;
       border-radius:10px;font-weight:600;font-size:13px;">View Full Results →</a>
  </div>
  <div style="padding:16px 36px;background:#F8FAFC;border-top:1px solid #F3F4F6;">
    <div style="font-size:11px;color:#9CA3AF;text-align:center;">
      Calipr AI · IITRAM Flux 2.0 · Sponsored by
      <span style="color:#E5E7EB;font-weight:700;">Redrob AI</span></div>
  </div>
</div></body></html>"""

def send_email_digest(ranked_candidates, job_title="Senior AI Engineer",
                      runtime=0.0, to_email=None):
    from integrations.config import SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, RECRUITER_EMAIL, SMTP_FROM_EMAIL
    
    recipient = to_email or RECRUITER_EMAIL
    if not recipient or not SMTP_SERVER:
        return {"success":False,"message":"SMTP or recipient not configured."}
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🏆 Calipr — {len(ranked_candidates):,} ranked for {job_title}"
        msg["From"] = SMTP_FROM_EMAIL
        msg["To"] = recipient
        
        if not SMTP_PASSWORD:
            return {"success": False, "message": "Missing SendGrid API Key or SMTP Password in Hugging Face Secrets. Please configure SENDGRID_API_KEY in Space Settings -> Variables and Secrets."}

        html_content = build_email_html(ranked_candidates, job_title, runtime)
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
            
        log_activity("Email","📧",f"Digest sent to *{recipient}* — top 10 of {len(ranked_candidates):,}","success")
        return {"success":True,"message":f"Email sent to {recipient}"}
    except Exception as e:
        return {"success":False,"message":str(e)}
