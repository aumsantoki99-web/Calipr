import os, json
import streamlit as st

def get_secret(key, default=""):
    # First check st.secrets, then os.environ
    try:
        return st.secrets.get(key, os.environ.get(key, default))
    except Exception:
        return os.environ.get(key, default)

SLACK_WEBHOOK_URL      = get_secret("SLACK_WEBHOOK_URL", "")
SENDGRID_API_KEY       = get_secret("SENDGRID_API_KEY", "")
RECRUITER_EMAIL        = get_secret("RECRUITER_EMAIL", "")
GOOGLE_SHEETS_ID       = get_secret("GOOGLE_SHEETS_ID", "")
GOOGLE_SERVICE_ACCOUNT = get_secret("GOOGLE_SERVICE_ACCOUNT", "{}")
CALIPR_API_KEY         = get_secret("CALIPR_API_KEY", "")

def get_google_creds():
    try:
        return json.loads(GOOGLE_SERVICE_ACCOUNT)
    except:
        return {}
