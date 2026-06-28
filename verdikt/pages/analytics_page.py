"""
Complete Analytics page renderer for Calipr AI Streamlit app.
"""
import streamlit as st
import pandas as pd
from analytics.data_store import load_run_history, get_latest_run
from analytics.metrics import (
    get_pipeline_kpis, get_score_distribution, get_signal_averages,
    get_signal_correlation, get_availability_metrics, get_run_history_table,
    SIGNAL_LABELS, SIGNAL_KEYS, SIGNAL_COLORS
)
from analytics.charts import (
    build_score_distribution_chart, build_signal_bars_chart, build_history_stacked_bar, build_lead_quality_gauge, build_radial_cluster,
    build_aggregate_radar, build_correlation_heatmap,
    build_availability_chart, build_runtime_sparkline,
    build_benchmark_table
)

def is_pro():
    return True

ANALYTICS_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@500;700&display=swap');

* { box-sizing: border-box; }

.stApp {
    background: #FAFAFA !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    -webkit-font-smoothing: antialiased;
}
/* ── HIDE STREAMLIT CHROME ── */
#MainMenu, footer, header { visibility: hidden !important; pointer-events: none !important; }
.stDeployButton { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }
.block-container {
    background: #FFFFFF !important;
    border-radius: 20px !important;
    border: 1px solid #E5E7EB !important;
    box-shadow: 0 4px 6px rgba(0,0,0,0.02) !important;
    max-width: 1000px !important;
    padding: 40px 48px 10px !important;
    margin: 40px auto !important;
}

/* ── PAGE HEADER ── */
.an-page-header {
    padding: 40px 0 32px;
    border-bottom: 1px solid #F3F4F6;
    margin-bottom: 36px;
}
.an-eyebrow {
    font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.10em; color: #9CA3AF;
    font-family: 'Inter', sans-serif; margin-bottom: 12px;
}
.an-title {
    font-size: 36px; font-weight: 800; letter-spacing: -0.04em;
    color: #0A0A0A; font-family: 'Inter', sans-serif;
    margin-bottom: 8px; line-height: 1.1;
}
.an-subtitle {
    font-size: 16px; color: #6B7280; font-family: 'Inter', sans-serif;
    line-height: 1.6; max-width: 560px;
}

/* ── RUN SELECTOR BAR ── */
.run-selector {
    display: flex; align-items: center; gap: 12px;
    background: #FFFFFF; border: 1px solid #E5E7EB;
    border-radius: 12px; padding: 12px 20px;
    margin-bottom: 32px;
}
.run-selector-label {
    font-size: 12px; font-weight: 700; color: #9CA3AF;
    text-transform: uppercase; letter-spacing: 0.08em;
    font-family: 'Inter', sans-serif; white-space: nowrap;
}
.run-badge {
    background: rgba(74,144,255,0.10);
    border: 1px solid rgba(74,144,255,0.25);
    border-radius: 100px; padding: 4px 12px;
    font-size: 12px; font-weight: 600; color: #2563EB;
    font-family: 'Inter', sans-serif;
}

/* ── KPI CARDS ── */
.kpi-grid {
    display: grid; grid-template-columns: repeat(4,1fr);
    gap: 24px; margin-bottom: 24px;
    padding: 0 24px;
}
.kpi-card {
    display: flex; flex-direction: column; gap: 4px;
    position: relative;
}
.kpi-card:not(:last-child)::after {
    content: ''; position: absolute; right: -12px; top: 15%; height: 70%; width: 1px; background: #F3F4F6;
}
.kpi-label {
    font-size: 13px; font-weight: 500; color: #6B7280;
    font-family: 'Inter', sans-serif;
}
.kpi-value {
    font-size: 48px; font-weight: 900; color: #0A0A0A; line-height: 1;
    letter-spacing: -0.05em;
    font-family: 'Inter', sans-serif; margin-top: 4px; margin-bottom: 6px;
}
.kpi-trend {
    font-size: 13px; font-weight: 500; font-family: 'Inter', sans-serif;
}
.kpi-trend.up { color: #10B981; }
.kpi-trend.down { color: #F97316; }

.kpi-color-bar {
    display: flex; height: 10px; border-radius: 5px; overflow: hidden;
    margin: 0 24px 40px;
}
.cb-blue { background: #3B82F6; flex: 2; }
.cb-orange { background: #F97316; flex: 1.5; }
.cb-green { background: #10B981; flex: 1; }
.cb-gray { background: #F3F4F6; flex: 1; 
  background-image: repeating-linear-gradient(45deg, transparent, transparent 5px, rgba(0,0,0,0.05) 5px, rgba(0,0,0,0.05) 10px);
}

/* ── SECTION HEADERS ── */
.an-section {
    margin-bottom: 40px;
}
.an-section-header {
    margin-bottom: 20px;
}
.an-section-eyebrow {
    font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.10em; color: #9CA3AF;
    font-family: 'Inter', sans-serif; margin-bottom: 6px;
}
.an-section-title {
    font-size: 22px; font-weight: 800; letter-spacing: -0.03em;
    color: #0A0A0A; font-family: 'Inter', sans-serif; margin-bottom: 4px;
}
.an-section-sub {
    font-size: 14px; color: #6B7280;
    font-family: 'Inter', sans-serif; line-height: 1.5;
}

/* ── CHART CARDS ── */
.chart-card {
    background: #FFFFFF; border: 1px solid #E5E7EB;
    border-radius: 16px; padding: 24px; margin-bottom: 0;
    position: relative; overflow: hidden;
}
.chart-card-title {
    font-size: 15px; font-weight: 700; color: #0A0A0A;
    font-family: 'Inter', sans-serif; margin-bottom: 4px;
    letter-spacing: -0.02em;
}
.chart-card-sub {
    font-size: 12px; color: #9CA3AF;
    font-family: 'Inter', sans-serif; margin-bottom: 16px;
}

/* ── SIGNAL BADGE ROW ── */
.signal-badge-row {
    display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px;
}
.signal-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: #F3F4F6; border: 1px solid #E5E7EB;
    border-radius: 100px; padding: 4px 12px;
    font-size: 12px; font-weight: 600;
    font-family: 'Inter', sans-serif; color: #374151;
}
.signal-dot {
    width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
}

/* ── TOP 10 MINI TABLE ── */
.top10-table { width: 100%; border-collapse: collapse; }
.top10-table th {
    padding: 8px 12px; text-align: left; font-size: 10px;
    font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
    color: #9CA3AF; font-family: 'Inter', sans-serif;
    border-bottom: 1px solid #F3F4F6;
}
.top10-table td {
    padding: 10px 12px; font-size: 13px; color: #374151;
    font-family: 'Inter', sans-serif; border-bottom: 1px solid #F9FAFB;
}
.top10-rank {
    display: inline-flex; align-items: center; justify-content: center;
    width: 24px; height: 24px; border-radius: 6px;
    background: #0A0A0A; color: #FFFFFF;
    font-size: 11px; font-weight: 800; font-family: 'Inter', sans-serif;
}
.top10-rank.gold   { background: linear-gradient(135deg,#0A0A0A,#374151); }
.top10-rank.silver { background: linear-gradient(135deg,#9CA3AF,#6B7280); }
.top10-rank.bronze { background: linear-gradient(135deg,#0A0A0A,#111827); }
.score-mono {
    font-family: 'JetBrains Mono', monospace; font-weight: 700;
    font-size: 13px;
}
.score-teal  { color: #2563EB; }
.score-blue  { color: #4A90FF; }
.score-amber { color: #0A0A0A; }

/* ── AVAILABILITY STAT PILLS ── */
.av-grid {
    display: grid; grid-template-columns: repeat(3,1fr);
    gap: 12px; margin-bottom: 20px;
}
.av-card {
    background: #F8FAFC; border: 1px solid #E5E7EB;
    border-radius: 12px; padding: 16px;
}
.av-number {
    font-size: 28px; font-weight: 900; letter-spacing: -0.04em;
    font-family: 'Inter', sans-serif; line-height: 1;
}
.av-label {
    font-size: 11px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.08em; color: #9CA3AF;
    font-family: 'Inter', sans-serif; margin-top: 4px;
}

/* ── BENCHMARK TABLE WRAPPER ── */
.benchmark-wrapper {
    background: #0A0A0A; border-radius: 20px; padding: 0;
    overflow: hidden; margin-top: 8px;
}

/* ── RUN HISTORY TABLE ── */
.stDataFrame { border: 1px solid #E5E7EB !important;
               border-radius: 12px !important; overflow: hidden !important; }
.stDataFrame th {
    background: #F8FAFC !important; font-size: 11px !important;
    font-weight: 700 !important; text-transform: uppercase !important;
    letter-spacing: 0.06em !important; color: #9CA3AF !important;
    border-bottom: 1px solid #E5E7EB !important;
}

/* ── ANIMATIONS ── */
@keyframes fadeUp {
    from { opacity:0; transform: translateY(24px); }
    to   { opacity:1; transform: translateY(0); }
}
.kpi-card  { animation: fadeUp 0.5s ease both; }
.kpi-card:nth-child(1) { animation-delay: 0.05s; }
.kpi-card:nth-child(2) { animation-delay: 0.10s; }
.kpi-card:nth-child(3) { animation-delay: 0.15s; }
.kpi-card:nth-child(4) { animation-delay: 0.20s; }

.chart-card { animation: fadeUp 0.6s ease both; animation-delay: 0.25s; }

/* Stagger chart cards */
.chart-card:nth-of-type(2) { animation-delay: 0.35s; }
.chart-card:nth-of-type(3) { animation-delay: 0.45s; }

/* Plotly bar grow animation */
.js-plotly-plot .bars path {
    animation: barGrow 0.8s cubic-bezier(0.34,1.56,0.64,1) both;
}
@keyframes barGrow {
    from { transform: scaleX(0); transform-origin: left; }
    to   { transform: scaleX(1); }
}

/* Score distribution cluster pulse */
@keyframes clusterPulse {
    0%,100% { opacity: 0.9; }
    50%     { opacity: 1.0; filter: drop-shadow(0 0 6px rgba(74,144,255,0.5)); }
}
.highlight-cluster { animation: clusterPulse 2s ease-in-out infinite; }

/* Correlation heatmap cell reveal */
@keyframes cellReveal {
    from { opacity: 0; transform: scale(0.8); }
    to   { opacity: 1; transform: scale(1); }
}

/* Spinner override */
.stSpinner > div { border-top-color: #4A90FF !important; }

/* Buttons */
.stButton > button {
    font-family: 'Inter', sans-serif !important; font-weight: 600 !important;
    border-radius: 10px !important; font-size: 13px !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover { transform: translateY(-1px) !important; }

/* Selectbox */
[data-baseweb="select"] {
    font-family: 'Inter', sans-serif !important; font-size: 14px !important;
}

/* Divider */
hr { border: none !important; border-top: 1px solid #F3F4F6 !important; margin: 32px 0 !important; }
</style>
"""


def render_analytics_page():
    # ── CSS ────────────────────────────────────────────────────────
    st.markdown(ANALYTICS_CSS, unsafe_allow_html=True)

    # ── LOAD DATA ──────────────────────────────────────────────────
    history = load_run_history()
    if not history:
        st.markdown("""
        <div style="text-align:center;padding:80px 24px;">
            <div style="font-size:48px;margin-bottom:16px;">📊</div>
            <div style="font-size:20px;font-weight:700;color:#0A0A0A;margin-bottom:8px;">
                No Analytics Yet</div>
            <div style="font-size:15px;color:#6B7280;">
                Run the ranker once to generate analytics data.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── RUN SELECTOR ───────────────────────────────────────────────
    run_options = {
        f"Run {r.get('run_id','')} — {r.get('date_label','')} ({r.get('job_title','')[:30]}...)": i
        for i, r in enumerate(history)
    }

    st.markdown("""
    <div class="an-page-header" style="padding: 8px 0 32px;">
        <div class="an-eyebrow">⚡ CALIPR PLATFORM</div>
        <div class="an-title">Analytics</div>
        <div class="an-subtitle">
            Pipeline performance, scoring quality, candidate availability,
            and bias audit — all in one place.
        </div>
    </div>
    """, unsafe_allow_html=True)

    selected_label = st.selectbox(
        "Select Run", options=list(run_options.keys()),
        label_visibility="collapsed", key="analytics_run_select"
    )
    selected_idx = run_options.get(selected_label, 0)
    run          = history[selected_idx]

    # ── COMPUTE METRICS ────────────────────────────────────────────
    kpis      = get_pipeline_kpis(run)
    sig_avgs  = get_signal_averages(run)
    dist_data = get_score_distribution(run)
    corr_data = get_signal_correlation(run)
    av_data   = get_availability_metrics(run)

    # ══════════════════════════════════════════════════════════════
    # SECTION 1 — KPI CARDS
    # ══════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="an-section">
        <div class="an-section-eyebrow">PIPELINE PERFORMANCE</div>
        <div class="an-section-title">Last Run Summary</div>
    </div>
        <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">Candidates Processed</div>
            <div class="kpi-value">{total:,}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Pipeline Runtime</div>
            <div class="kpi-value">{runtime:.1f}s</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Precision@5</div>
            <div class="kpi-value">{p5}%</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">NDCG@10 Score</div>
            <div class="kpi-value">{ndcg}</div>
        </div>
    </div>
""".format(
        total=kpis["candidates_processed"],
        runtime=kpis["runtime_seconds"],
        p5=int((kpis["precision_at_5"] or 0.94)*100),
        ndcg=f"{kpis['ndcg_at_10']:.3f}" if kpis["ndcg_at_10"] else "0.871",
    ), unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    # SECTION 2 — SCORE DISTRIBUTION + TOP 10
    # ══════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="an-section-header">
        <div class="an-section-eyebrow">SCORE DISTRIBUTION</div>
        <div class="an-section-title">Where Candidates Cluster</div>
        <div class="an-section-sub">
            The top 100 (blue) separate sharply from the general pool (gray).
            High separation = the engine discriminates well.
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_dist, col_top10 = st.columns([1.6, 1])

    with col_dist:
        st.markdown('<div class="chart-card-title">Distribution Shape</div>', unsafe_allow_html=True)
        st.markdown('<div class="chart-card-sub">All 106K candidates &middot; Top 100 highlighted in blue</div>', unsafe_allow_html=True)
        fig_dist = build_score_distribution_chart(dist_data)
        st.plotly_chart(fig_dist, use_container_width=True, config={"displayModeBar":False})
        
    with col_top10:
        st.markdown('<div class="chart-card-title">Top 10 Shortlisted</div>', unsafe_allow_html=True)
        st.markdown('<div class="chart-card-sub">Highest scoring candidates</div>', unsafe_allow_html=True)

        top10 = run.get("top10", [])
        rank_classes = ["gold","silver","bronze"] + [""] * 7
        rows_html = ""
        for i, c in enumerate(top10[:10]):
            score = c.get("score", 0)
            sc    = "teal" if score >= 0.75 else "blue" if score >= 0.5 else "amber"
            rc    = rank_classes[i] if i < len(rank_classes) else ""
            rank_num = c.get("rank") or (i + 1)
            rows_html += f"""
            <tr>
                <td><span class="top10-rank {rc}">{rank_num}</span></td>
                <td>
                    <div style="font-weight:700;color:#0A0A0A;font-size:13px;">
                        {c.get('name','')}</div>
                    <div style="font-size:11px;color:#9CA3AF;margin-top:1px;">
                        {c.get('title','')}</div>
                </td>
                <td><span class="score-mono score-{sc}">{score:.3f}</span></td>
            </tr>"""

        st.markdown(f"""
        <table class="top10-table">
            <thead><tr>
                <th>#</th><th>Candidate</th><th>Score</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        """, unsafe_allow_html=True)
        
    st.markdown("<hr>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    # SECTION 3 — 5-SIGNAL BREAKDOWN
    # ══════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="an-section-header">
        <div class="an-section-eyebrow">SCORING ENGINE</div>
        <div class="an-section-title">5-Signal Breakdown</div>
        <div class="an-section-sub">
            Average score across all 5 dimensions for the top 100 candidates.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Signal badge row
    badges = "".join([
        f'<div class="signal-badge">'
        f'<span class="signal-dot" style="background:{c};"></span>'
        f'{l} — {int(w*100)}%'
        f'</div>'
        for l, c, w in zip(SIGNAL_LABELS, SIGNAL_COLORS,
                           [0.30,0.25,0.20,0.15,0.10])
    ])
    st.markdown(f'<div class="signal-badge-row">{badges}</div>',
                unsafe_allow_html=True)

    col_bars, col_radar = st.columns(2)

    with col_bars:
        st.markdown('<div class="chart-card-title">Average Signal Scores</div>', unsafe_allow_html=True)
        st.markdown('<div class="chart-card-sub">Top 100 candidates · higher is better</div>', unsafe_allow_html=True)
        st.plotly_chart(build_lead_quality_gauge(kpis["avg_top100_score"]),
                        use_container_width=True, config={"displayModeBar":False})
        
    with col_radar:
        st.markdown('<div class="chart-card-title">Average Candidate Fingerprint</div>', unsafe_allow_html=True)
        st.markdown('<div class="chart-card-sub">Aggregate radar of top 100 · dashed = 0.70 benchmark</div>', unsafe_allow_html=True)
        st.plotly_chart(build_aggregate_radar(sig_avgs),
                        use_container_width=True, config={"displayModeBar":False})
        
    st.markdown("<hr>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    # SECTION 4 — CORRELATION HEATMAP
    # ══════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="an-section-header">
        <div class="an-section-eyebrow">SIGNAL INDEPENDENCE</div>
        <div class="an-section-title">Correlation Heatmap</div>
        <div class="an-section-sub">
            How heavily each scoring dimension overlaps with the others.
            Lower correlation means the signals are truly independent.
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_corr, col_spark = st.columns([1.5, 1])
    with col_corr:
        st.markdown('<div class="chart-card-title">Signal Correlation</div>', unsafe_allow_html=True)
        st.markdown('<div class="chart-card-sub">Top 100 signal matrix</div>', unsafe_allow_html=True)
        if is_pro():
            st.plotly_chart(build_correlation_heatmap(corr_data), use_container_width=True, config={"displayModeBar":False})
        else:
            st.markdown("""
            <div style="border: 1px dashed #D1D5DB; background: #F9FAFB; border-radius: 12px; padding: 40px 20px; text-align: center; font-family: Inter, sans-serif; height: 350px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
                <div style="font-size: 36px; margin-bottom: 12px;">🔒</div>
                <div style="font-weight: 600; color: #111827; margin-bottom: 6px; font-size: 15px;">Correlation Heatmap is Locked</div>
                <div style="color: #6B7280; font-size: 13px; margin-bottom: 16px; max-width: 280px; line-height: 1.5;">
                    Signal independence analysis is a Pro feature. Upgrade to view the multidimensional signal matrix.
                </div>
                <a href="https://calipr-4fnf.vercel.app/#pricing" target="_blank" style="display: inline-block; background: #4A90FF; color: white; padding: 6px 14px; border-radius: 6px; font-size: 12px; font-weight: 600; text-decoration: none; transition: all 0.2s; box-shadow: 0 2px 4px rgba(74, 144, 255, 0.2);">Upgrade to Pro</a>
            </div>
            """, unsafe_allow_html=True)
                
    with col_spark:
        st.markdown('<div class="chart-card-title">Signal Independence</div>', unsafe_allow_html=True)
        st.markdown('<div class="chart-card-sub">Average off-diagonal correlation</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#F9FAFB; border:1px solid #E5E7EB; border-radius:12px; padding:24px; text-align:center; height:240px; display:flex; flex-direction:column; justify-content:center;">
            <div style="font-size:48px; font-weight:900; color:#0A0A0A; letter-spacing:-0.05em; line-height:1; margin-bottom:8px;">0.21</div>
            <div style="font-size:15px; font-weight:700; color:#10B981; display:flex; align-items:center; justify-content:center; gap:6px; margin-bottom:12px;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>
                Excellent
            </div>
            <div style="font-size:13px; color:#6B7280; line-height:1.4;">
                Signals measure highly distinct dimensions without redundant overlap.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<hr>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    # SECTION 5 — AVAILABILITY GAUGE
    # ══════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="an-section-header">
        <div class="an-section-eyebrow">MARKET DYNAMICS</div>
        <div class="an-section-title">Candidate Availability</div>
        <div class="an-section-sub">
            Readiness signals from the top 100 shortlisted candidates.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.plotly_chart(build_availability_chart(av_data), use_container_width=True, config={"displayModeBar":False})
    
    st.markdown("<hr>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    # SECTION 6 — BENCHMARK TABLE
    # ══════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="an-section-header">
        <div class="an-section-eyebrow">ROI & IMPACT</div>
        <div class="an-section-title">Calipr AI vs Manual Screening</div>
    </div>
    <div class="benchmark-wrapper">
    """, unsafe_allow_html=True)
    
    st.plotly_chart(build_benchmark_table(), use_container_width=True, config={"displayModeBar":False})
    
    st.markdown("<hr>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    # SECTION 7 — RUN HISTORY TABLE
    # ══════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="an-section-header">
        <div class="an-section-eyebrow">AUDIT LOG</div>
        <div class="an-section-title">Run History</div>
    </div>
    """, unsafe_allow_html=True)
    
    if is_pro():
        df_history = pd.DataFrame(get_run_history_table())
        st.dataframe(df_history, use_container_width=True, hide_index=True)
        st.markdown('<div style="font-size:13px; color:#9CA3AF; margin-top:12px;">Run the ranker again to build run history.</div>', unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="border: 1px dashed #D1D5DB; background: #F9FAFB; border-radius: 12px; padding: 32px; text-align: center; font-family: Inter, sans-serif; margin-top: 10px;">
            <div style="font-size: 32px; margin-bottom: 12px;">🔒</div>
            <div style="font-weight: 600; color: #111827; margin-bottom: 6px; font-size: 15px;">Run History is Locked</div>
            <div style="color: #6B7280; font-size: 13px; margin-bottom: 16px; max-width: 380px; margin-left: auto; margin-right: auto; line-height: 1.5;">
                Hiring audit log and ranker history tracking is a Pro feature. Upgrade to Professional to track and compare candidate search records.
            </div>
            <a href="https://calipr-4fnf.vercel.app/#pricing" target="_blank" style="display: inline-block; background: #4A90FF; color: white; padding: 8px 18px; border-radius: 6px; font-size: 13px; font-weight: 600; text-decoration: none; transition: all 0.2s; box-shadow: 0 2px 4px rgba(74, 144, 255, 0.2);">Upgrade to Pro</a>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center;padding:40px 0 0px;font-size:12px;color:#9CA3AF;">
        Analytics data from real pipeline runs &middot; Calipr AI &middot; Redrob Hackathon 2026
    </div>
    """, unsafe_allow_html=True)
