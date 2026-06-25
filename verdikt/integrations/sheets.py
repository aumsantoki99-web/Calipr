from datetime import datetime
from integrations.config import GOOGLE_SHEETS_ID, get_google_creds
from integrations.activity_log import log_activity

def get_sheets_client():
    import gspread
    from google.oauth2.service_account import Credentials
    creds = get_google_creds()
    if not creds:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT not configured.")
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
    return gspread.authorize(Credentials.from_service_account_info(creds, scopes=scopes))

def export_to_sheets(ranked_candidates, job_title=""):
    if not GOOGLE_SHEETS_ID:
        return {"success":False,"message":"GOOGLE_SHEETS_ID not configured."}
    try:
        client = get_sheets_client()
        ss     = client.open_by_key(GOOGLE_SHEETS_ID)
        ts     = datetime.now().strftime("%d %b %Y %H:%M")
        try:
            ws = ss.add_worksheet(title=f"Run — {ts}", rows=200, cols=15)
        except:
            ws = ss.sheet1

        headers = ["Rank","Candidate ID","Name","Current Title","Years Exp",
                   "Final Score","Semantic","Skills","Career","Behavioral",
                   "Domain","AI Rationale","Open to Work","Notice Days","Response Rate"]

        rows = [headers]
        for c in ranked_candidates:
            rs = c.get("redrob_signals", {})
            rows.append([
                c.get("rank",""),
                c.get("candidate_id", c.get("id","")),
                c.get("name", c.get("profile",{}).get("anonymized_name","")),
                c.get("current_title", c.get("profile",{}).get("current_title","")),
                c.get("years_of_experience", c.get("years_experience",
                      c.get("profile",{}).get("years_of_experience",""))),
                round(c.get("score", c.get("final_score",0)), 4),
                round(c.get("s1_semantic",0), 4),
                round(c.get("s2_skills",0), 4),
                round(c.get("s3_career",0), 4),
                round(c.get("s4_behavioral",0), 4),
                round(c.get("s5_domain",0), 4),
                c.get("reasoning", c.get("ai_recruiter_rationale","")),
                "Yes" if rs.get("open_to_work_flag") else "No",
                rs.get("notice_period_days",""),
                rs.get("recruiter_response_rate","")
            ])

        ws.update("A1", rows)
        ws.format("A1:O1", {
            "backgroundColor":{"red":0.04,"green":0.04,"blue":0.04},
            "textFormat":{"foregroundColor":{"red":1,"green":1,"blue":1},
                          "bold":True,"fontSize":11}
        })
        ws.freeze(rows=1)

        url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}"
        log_activity("Google Sheets","📊",
                     f"Exported {len(ranked_candidates)} candidates to *Calipr Rankings — {ts}*","success")
        return {"success":True,"message":f"Exported {len(ranked_candidates)} candidates.","sheet_url":url}
    except Exception as e:
        return {"success":False,"message":f"Sheets error: {str(e)}"}

def get_sheet_url():
    return f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}" if GOOGLE_SHEETS_ID else ""
