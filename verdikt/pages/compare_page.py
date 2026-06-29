import streamlit as st
import pandas as pd

def render_compare_page():
    st.markdown("""
    <style>
    .compare-header {
        font-family: 'Open Runde', sans-serif;
        font-size: 28px;
        font-weight: 800;
        color: #1a1615;
        margin-bottom: 8px;
        letter-spacing: -0.03em;
    }
    .compare-subtitle {
        font-family: Inter, sans-serif;
        font-size: 15px;
        color: #757170;
        margin-bottom: 24px;
    }
    .shortlist-box {
        background: #ffffff;
        border: 1px solid #e4e2e2;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    .weight-pill {
        display: inline-block;
        background: #F3F4F6;
        color: #4B5563;
        padding: 4px 10px;
        border-radius: 100px;
        font-size: 11px;
        font-weight: 600;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    .cand-card {
        padding: 12px;
        border-bottom: 1px solid #f0f0f0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .cand-card:last-child {
        border-bottom: none;
    }
    .cand-rank {
        font-weight: 700;
        color: #9CA3AF;
        width: 24px;
    }
    .cand-name {
        font-weight: 600;
        color: #111827;
        font-size: 14px;
    }
    .cand-score {
        font-weight: 700;
        color: #0c7540;
        background: rgba(14,161,88,0.1);
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 12px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="compare-header">Compare Shortlists</div>', unsafe_allow_html=True)
    st.markdown('<div class="compare-subtitle">Evaluate how different weight configurations impact your top 10 candidates.</div>', unsafe_allow_html=True)
    
    if "saved_shortlists" not in st.session_state or len(st.session_state.saved_shortlists) == 0:
        st.info("No shortlists saved yet. Go back to the Candidate Ranker, run a ranking, and click 'Save Shortlist for Comparison'.")
        return
        
    shortlists = st.session_state.saved_shortlists
    
    if len(shortlists) < 2:
        st.warning("You have only saved one shortlist. Save at least one more with different weights to compare them!")
        
    options = {s["name"]: s for s in shortlists}
    
    col1, col2 = st.columns(2)
    
    with col1:
        sel1 = st.selectbox("Select List A", list(options.keys()), index=0)
    with col2:
        sel2 = st.selectbox("Select List B", list(options.keys()), index=min(1, len(options)-1))
        
    s1 = options[sel1]
    s2 = options[sel2]
    
    def render_shortlist(s):
        w = s["weights"]
        st.markdown(f"""
        <div class="shortlist-box">
            <h3 style="margin-top:0;font-size:18px;color:#111827;">{s["name"]}</h3>
            <div style="margin-bottom:16px;">
                <span class="weight-pill">Sem: {w.get('sem', 0):.1f}%</span>
                <span class="weight-pill">Skl: {w.get('skl', 0):.1f}%</span>
                <span class="weight-pill">Car: {w.get('car', 0):.1f}%</span>
                <span class="weight-pill">Beh: {w.get('beh', 0):.1f}%</span>
                <span class="weight-pill">Dom: {w.get('dom', 0):.1f}%</span>
            </div>
            <div style="border:1px solid #e4e2e2; border-radius:8px; overflow:hidden;">
        """, unsafe_allow_html=True)
        
        for i, c in enumerate(s["candidates"]):
            st.markdown(f"""
            <div class="cand-card">
                <div style="display:flex; align-items:center;">
                    <div class="cand-rank">#{i+1}</div>
                    <div class="cand-name">{c.get('name', 'Unknown')}</div>
                </div>
                <div class="cand-score">{c.get('score', 0):.2f}</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown('</div></div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        render_shortlist(s1)
    with c2:
        render_shortlist(s2)
        
    # Analysis
    s1_names = set([c.get('name') for c in s1["candidates"]])
    s2_names = set([c.get('name') for c in s2["candidates"]])
    overlap = s1_names.intersection(s2_names)
    
    st.markdown("### Analysis")
    st.markdown(f"**{len(overlap)} candidates** appear in both Top 10 shortlists.")
    if len(overlap) > 0:
        st.markdown(f"Overlapping candidates: {', '.join(overlap)}")
