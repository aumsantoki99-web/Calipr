import json
from datetime import datetime
from auth.supabase_auth import get_supabase_client

def save_ranking_run(user_id: str, job_title: str, runtime_seconds: float, ranked_candidates: list) -> bool:
    """
    Saves a ranking run to the Supabase ranking_history table.
    """
    client = get_supabase_client()
    if not client:
        return False
        
    try:
        data = {
            "user_id": user_id,
            "job_title": job_title,
            "runtime_seconds": runtime_seconds,
            "ranked_candidates": ranked_candidates
        }
        
        response = client.table("ranking_history").insert(data).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error saving to DB: {e}")
        return False

def fetch_past_runs(user_id: str) -> list:
    """
    Fetches the past ranking runs for a given user, ordered by newest first.
    Returns a list of dictionaries.
    """
    client = get_supabase_client()
    if not client:
        return []
        
    try:
        response = client.table("ranking_history")\
            .select("id, job_title, runtime_seconds, created_at, ranked_candidates")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()
        return response.data
    except Exception as e:
        print(f"Error fetching from DB: {e}")
        return []
