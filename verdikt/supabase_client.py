# supabase_client.py
import os
from supabase import create_client, Client

# Try to load local .env if python-dotenv is installed (useful for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SUPABASE_URL  = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY  = os.environ.get("SUPABASE_ANON_KEY", "")

def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment. "
            "Add them to HuggingFace Space secrets or local .env file."
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)
