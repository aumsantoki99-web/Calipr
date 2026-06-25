import json, os
from datetime import datetime

WAITLIST_PATH = "data/waitlist.json"

def load_waitlist():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(WAITLIST_PATH): return []
    try:
        with open(WAITLIST_PATH) as f: return json.load(f)
    except: return []

def add_to_waitlist(email, integration="general"):
    if not email or "@" not in email:
        return {"success":False,"message":"Invalid email."}
    wl = load_waitlist()
    existing = next((e for e in wl if e["email"]==email.lower()),None)
    if existing:
        return {"success":False,"message":f"Already on waitlist since {existing['joined_at'][:10]}","duplicate":True}
    entry = {"email":email.lower().strip(),"integration":integration,
             "joined_at":datetime.utcnow().isoformat()}
    wl.append(entry)
    with open(WAITLIST_PATH,"w") as f: json.dump(wl,f,indent=2)
    return {"success":True,"message":f"Added to {integration} waitlist!","total":len(wl)}

def get_waitlist_count(): return len(load_waitlist())

def export_waitlist_csv():
    import csv, io
    wl = load_waitlist()
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=["email","integration","joined_at"])
    w.writeheader(); w.writerows(wl)
    return out.getvalue().encode("utf-8")
