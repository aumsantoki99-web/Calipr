import json, os
from datetime import datetime

ACTIVITY_PATH = "data/activity_log.json"
MAX_ENTRIES   = 50

def log_activity(integration, icon, message, status="success"):
    os.makedirs("data", exist_ok=True)
    entries = load_activity()
    entries.insert(0,{"integration":integration,"icon":icon,"message":message,
                       "status":status,"timestamp":datetime.utcnow().isoformat(),
                       "time_label":"just now"})
    entries = entries[:MAX_ENTRIES]
    with open(ACTIVITY_PATH,"w") as f: json.dump(entries,f,indent=2)

def _relative(dt):
    d = (datetime.utcnow()-dt).total_seconds()
    if d<60: return f"{int(d)}s ago"
    if d<3600: return f"{int(d/60)} min ago"
    if d<86400: return f"{int(d/3600)} hr ago"
    return f"{int(d/86400)} days ago"

def load_activity():
    if not os.path.exists(ACTIVITY_PATH): return _defaults()
    try:
        with open(ACTIVITY_PATH) as f: entries = json.load(f)
        for e in entries:
            try: e["time_label"] = _relative(datetime.fromisoformat(e["timestamp"]))
            except: pass
        return entries
    except: return _defaults()

def _defaults():
    return [
        {"integration":"Slack","icon":"💬","message":"Sent top 5 candidates for *Senior AI Engineer* to #recruiting","status":"success","timestamp":datetime.utcnow().isoformat(),"time_label":"2 min ago"},
        {"integration":"Google Sheets","icon":"📊","message":"Exported 100 candidates to *Calipr Rankings — Redrob Challenge 2025*","status":"success","timestamp":datetime.utcnow().isoformat(),"time_label":"5 min ago"},
        {"integration":"CSV Export","icon":"📄","message":"submission.csv generated — 100 rows, validated ✓","status":"success","timestamp":datetime.utcnow().isoformat(),"time_label":"8 min ago"},
    ]
