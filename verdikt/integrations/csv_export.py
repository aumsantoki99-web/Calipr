import csv, io, os, re
from datetime import datetime
from integrations.activity_log import log_activity

def generate_submission_csv(ranked_candidates):
    """Returns (csv_bytes, filename). Validates before returning."""
    if len(ranked_candidates) < 100:
        raise ValueError(f"Need 100 candidates, got {len(ranked_candidates)}")

    top100 = ranked_candidates[:100]
    pat    = re.compile(r"^CAND_\d{7}$")

    # Fix candidate_id format if needed
    for c in top100:
        cid = str(c.get("candidate_id", c.get("id","")))
        if not pat.match(cid):
            raw = cid.replace("CAND_","").strip()
            c["candidate_id"] = f"CAND_{int(raw):07d}" if raw.isdigit() else cid

    # Sort by score descending, tie-break ascending candidate_id
    top100.sort(key=lambda x: (
        -float(x.get("score", x.get("final_score",0))),
        x.get("candidate_id","")
    ))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["candidate_id","rank","score","reasoning"])

    for rank, c in enumerate(top100, 1):
        cid       = c.get("candidate_id", c.get("id",""))
        score     = round(float(c.get("score", c.get("final_score",0))),4)
        reasoning = c.get("reasoning", c.get("ai_recruiter_rationale",""))
        reasoning = reasoning.encode("ascii",errors="replace").decode("ascii")[:200]
        writer.writerow([cid, rank, score, reasoning])

    csv_bytes = output.getvalue().encode("utf-8")
    os.makedirs("outputs", exist_ok=True)
    with open("outputs/submission.csv","w",newline="",encoding="utf-8") as f:
        f.write(output.getvalue())

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"calipr_submission_{ts}.csv"
    log_activity("CSV Export","📄","submission.csv generated — 100 rows, validated ✓","success")
    return csv_bytes, filename

def validate_existing_csv(filepath="outputs/submission.csv"):
    errors, warnings = [], []
    if not os.path.exists(filepath):
        return {"valid":False,"errors":["File not found"],"warnings":[]}
    try:
        with open(filepath,"r",encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows   = list(reader)
        missing = [c for c in ["candidate_id","rank","score","reasoning"] if c not in (reader.fieldnames or [])]
        if missing: errors.append(f"Missing columns: {missing}")
        if len(rows) != 100: errors.append(f"Expected 100 rows, got {len(rows)}")
        pat  = re.compile(r"^CAND_\d{7}$")
        bads = [r["candidate_id"] for r in rows if not pat.match(r.get("candidate_id",""))]
        if bads: errors.append(f"Bad candidate_id format: {bads[:3]}")
        ranks = [int(r.get("rank",0)) for r in rows]
        if sorted(ranks) != list(range(1,101)): errors.append("Ranks not sequential 1-100")
        scores = [float(r.get("score",0)) for r in rows]
        for i in range(1,len(scores)):
            if scores[i] > scores[i-1]+1e-6:
                errors.append(f"Score not non-increasing at rank {i+1}"); break
        empty = sum(1 for r in rows if not r.get("reasoning","").strip())
        if empty: warnings.append(f"{empty} rows have empty reasoning")
    except Exception as e:
        errors.append(str(e))
    return {"valid":len(errors)==0,"errors":errors,"warnings":warnings}
