import os, json
import streamlit as st

def get_secret(key, default=""):
    # First check session_state, then st.secrets, then os.environ
    if key in st.session_state and st.session_state[key]:
        return st.session_state[key]
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

# ATS Webhooks
GREENHOUSE_WEBHOOK_URL = get_secret("GREENHOUSE_WEBHOOK_URL", "")
GREENHOUSE_API_KEY     = get_secret("GREENHOUSE_API_KEY", "")

# SMTP Configuration
SMTP_SERVER            = get_secret("SMTP_SERVER", "smtp.sendgrid.net")
SMTP_PORT              = int(get_secret("SMTP_PORT", "587"))
SMTP_USER              = get_secret("SMTP_USER", "apikey")
SMTP_PASSWORD          = get_secret("SMTP_PASSWORD", SENDGRID_API_KEY)
SMTP_FROM_EMAIL        = get_secret("SMTP_FROM_EMAIL", "noreply@calipr.ai")
def get_google_creds():
    try:
        return json.loads(GOOGLE_SERVICE_ACCOUNT)
    except:
        return {}
