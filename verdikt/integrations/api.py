import os, json, time, threading, uuid
from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
from integrations.config import CALIPR_API_KEY

api_app = FastAPI(title="Calipr AI API", version="1.0.0",
                  docs_url="/api/docs", redoc_url="/api/redoc")
api_app.add_middleware(CORSMiddleware, allow_origins=["*"],
                       allow_methods=["*"], allow_headers=["*"])

def verify_key(x_api_key=Header(None)):
    if CALIPR_API_KEY and x_api_key != CALIPR_API_KEY:
        raise HTTPException(401, "Invalid API key")

@api_app.get("/")
def root():
    return {"service":"Calipr AI API","docs":"/api/docs",
            "endpoints":{"rank":"POST /api/rank","health":"GET /api/health","download":"GET /api/download"}}

@api_app.get("/api/health")
def health(): return {"status":"ok","timestamp":time.time()}

@api_app.post("/api/rank")
async def rank(jd_text: str = Form(...), top_n: int = Form(100),
               candidates_file: UploadFile = File(None),
               x_api_key: str = Header(None)):
    verify_key(x_api_key)
    cpath = "data/candidates.jsonl"
    if candidates_file:
        content  = await candidates_file.read()
        cpath    = f"/tmp/cands_{int(time.time())}.jsonl"
        with open(cpath,"wb") as f: f.write(content)
    if not os.path.exists(cpath):
        raise HTTPException(400, "candidates.jsonl not found.")
    try:
        import subprocess
        job_id   = str(uuid.uuid4())[:8]
        out_path = f"/tmp/result_{job_id}.csv"
        t0       = time.time()
        res = subprocess.run(
            ["python","rank.py","--candidates",cpath,"--out",out_path],
            capture_output=True, text=True, timeout=360
        )
        runtime = round(time.time()-t0, 2)
        if res.returncode != 0:
            raise HTTPException(500, f"Ranking failed: {res.stderr[:300]}")
        import csv
        candidates_out = []
        if os.path.exists(out_path):
            with open(out_path) as f:
                candidates_out = list(csv.DictReader(f))
        return {"job_id":job_id,"status":"complete","runtime_seconds":runtime,
                "total_candidates":len(candidates_out),"ranked_candidates":candidates_out[:top_n]}
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Ranking timed out")
    except Exception as e:
        raise HTTPException(500, str(e))

@api_app.get("/api/download")
def download():
    p = "outputs/submission.csv"
    if not os.path.exists(p): raise HTTPException(404,"No CSV found. Run ranker first.")
    return FileResponse(p, media_type="text/csv", filename="calipr_submission.csv")

def start_api_server(port=7861):
    t = threading.Thread(target=lambda: uvicorn.run(api_app,host="0.0.0.0",port=port,log_level="error"), daemon=True)
    t.start()
    return t
