import streamlit as st
import json
from db_manager import fetch_past_runs

def render_history_page():
    st.markdown('<div class="page-header"><div class="page-title">Run History</div><div class="page-subtitle">Your past candidate rankings</div></div>', unsafe_allow_html=True)
    
    if not st.session_state.get("user"):
        st.warning("Please sign in to view your ranking history.")
        return
        
    runs = fetch_past_runs(st.session_state["user"].id)
    
    if not runs:
        st.info("No past ranking runs found. Go to 'Candidate Ranker' to run your first pipeline!")
        return
        
    for run in runs:
        date_str = run.get("created_at", "")
        # Format the date nicely if possible
        try:
            # Supabase returns ISO format
            from dateutil import parser
            dt = parser.parse(date_str)
            date_display = dt.strftime("%B %d, %Y at %I:%M %p")
        except:
            date_display = date_str
            
        candidates = run.get("ranked_candidates", [])
        top_name = candidates[0].get("name", "Unknown") if candidates else "None"
        
        with st.expander(f"{run.get('job_title', 'Role')} — {date_display}"):
            st.markdown(f"**Runtime**: {run.get('runtime_seconds', 0)} seconds | **Candidates Evaluated**: {len(candidates)}")
            st.markdown(f"**Top Candidate**: {top_name}")
            
            if st.button(f"Load this run into Ranker", key=f"load_{run['id']}"):
                st.session_state.scored_candidates = candidates
                st.session_state.job_title = run.get('job_title', 'Role')
                st.session_state.run_runtime = run.get('runtime_seconds', 0)
                st.toast("Run loaded! Switch to 'Candidate Ranker' tab to view.", icon="✅")
                
            # Preview top 5
            st.markdown("#### Top 5 Candidates")
            for i, c in enumerate(candidates[:5]):
                st.markdown(f"{i+1}. **{c.get('name')}** - Score: {c.get('score', 0)}")
