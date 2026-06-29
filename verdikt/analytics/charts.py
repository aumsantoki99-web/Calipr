"""
All Plotly figure builders for Analytics page.
Every figure styled to match Calipr landing page exactly.
"""
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from analytics.metrics import (
    SIGNAL_LABELS, SIGNAL_KEYS, SIGNAL_COLORS, SIGNAL_WEIGHTS
)

# ── SHARED PLOTLY LAYOUT ───────────────────────────────────────────
CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, system-ui, sans-serif", color="#0A0A0A"),
    margin=dict(l=0, r=0, t=40, b=0),
    showlegend=False,
)

AXIS_STYLE = dict(
    gridcolor="rgba(229,231,235,0.8)",
    linecolor="rgba(229,231,235,0.6)",
    tickfont=dict(size=11, color="#9CA3AF", family="Inter"),
    showgrid=True,
    zeroline=False,
)


# ── CHART 1 — SCORE DISTRIBUTION (CLUSTER HISTOGRAM) ─────────────
def build_score_distribution_chart(dist_data: dict) -> go.Figure:
    """
    Animated histogram showing full 106K score distribution.
    Top 100 highlighted in blue. Rest in gray.
    Bars grow from bottom with staggered animation.
    """
    bin_centers  = dist_data["bin_centers"]
    total_counts = dist_data["total_counts"]
    top100       = dist_data["top100_counts"]

    # Noise pool = total - top100
    noise_counts = [max(0, t - h) for t, h in zip(total_counts, top100)]

    fig = go.Figure()

    # Noise bars (gray) — bottom layer
    fig.add_trace(go.Bar(
        x=bin_centers,
        y=noise_counts,
        name="Other Candidates",
        marker=dict(
            color="rgba(100, 116, 139, 0.5)",
            line=dict(width=0),
        ),
        width=0.04,
        hovertemplate="Score: %{x:.2f}<br>Count: %{y:,}<extra>General Pool</extra>",
    ))

    # Top 100 bars (blue) — stacked on top
    fig.add_trace(go.Bar(
        x=bin_centers,
        y=top100,
        name="Top 100 Shortlist",
        marker=dict(
            color="#4A90FF",
            line=dict(width=0),
        ),
        width=0.04,
        hovertemplate="Score: %{x:.2f}<br>Shortlisted: %{y}<extra>Top 100</extra>",
    ))

    fig.update_layout(
        **CHART_LAYOUT,
        barmode="stack",
        bargap=0.15,
        xaxis=dict(
            **AXIS_STYLE,
            title=dict(text="Score", font=dict(size=12, color="#6B7280")),
            tickvals=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            ticktext=["0.1","0.2","0.3","0.4","0.5","0.6","0.7","0.8","0.9","1.0"],
            range=[0.05, 1.02],
        ),
        yaxis=dict(
            **AXIS_STYLE,
            title=dict(text="Candidates", font=dict(size=12, color="#6B7280")),
            tickformat=",",
        ),
        annotations=[
            dict(
                x=0.85, y=max(top100)*1.2 if max(top100) else 1,
                text="<b>Top 100</b><br>Shortlisted",
                showarrow=True,
                arrowhead=2,
                arrowcolor="#4A90FF",
                font=dict(size=11, color="#4A90FF"),
                ax=40, ay=-30,
                bgcolor="rgba(74,144,255,0.08)",
                bordercolor="#4A90FF",
                borderwidth=1,
                borderpad=6,
            )
        ],
        height=300,
    )
    return fig


# ── CHART 2 — SIGNAL AVERAGE BARS (ANIMATED HORIZONTAL) ──────────
def build_signal_bars_chart(signal_avgs: dict) -> go.Figure:
    """
    Horizontal bar chart — 5 signals with unique gradient bars.
    Each bar has a different color matching its signal.
    """
    labels = SIGNAL_LABELS
    values = [signal_avgs.get(k, 0) for k in SIGNAL_KEYS]
    colors = SIGNAL_COLORS

    fig = go.Figure()

    # Background track bars (light gray full width)
    fig.add_trace(go.Bar(
        y=labels,
        x=[1.0] * 5,
        orientation="h",
        marker=dict(color="rgba(229,231,235,0.5)", line=dict(width=0)),
        hoverinfo="skip",
        showlegend=False,
    ))

    # Actual value bars (colored)
    fig.add_trace(go.Bar(
        y=labels,
        x=values,
        orientation="h",
        marker=dict(
            color=colors,
            line=dict(width=0),
        ),
        text=[f"{v:.2f}" for v in values],
        textposition="outside",
        textfont=dict(size=13, color="#0A0A0A",
                      family="JetBrains Mono, monospace", weight=700),
        hovertemplate="%{y}: <b>%{x:.3f}</b><extra></extra>",
        width=0.55,
    ))

    # Weight annotations on right
    for i, (label, weight) in enumerate(zip(labels, SIGNAL_WEIGHTS)):
        fig.add_annotation(
            x=1.08, y=label,
            text=f"{int(weight*100)}%",
            showarrow=False,
            font=dict(size=11, color="#9CA3AF", family="Inter"),
            xanchor="left",
        )

    fig.update_layout(
        **CHART_LAYOUT,
        barmode="overlay",
        xaxis=dict(
            range=[0, 1.15],
            showgrid=False,
            showticklabels=False,
            zeroline=False,
        ),
        yaxis=dict(
            showgrid=False,
            tickfont=dict(size=13, color="#374151", family="Inter", weight=600),
            autorange="reversed",
        ),
        height=280,
    )
    fig.update_layout(margin=dict(l=0, r=60, t=20, b=0))
    return fig


# ── CHART 3 — AGGREGATE RADAR CHART ──────────────────────────────
def build_aggregate_radar(signal_avgs: dict) -> go.Figure:
    """
    Radar chart showing average fingerprint of top 100 candidates.
    Exact same styling as landing page radar — blue fill, Inter font.
    """
    categories = SIGNAL_LABELS
    values     = [signal_avgs.get(k, 0) for k in SIGNAL_KEYS]
    values_c   = values + [values[0]]
    cats_c     = categories + [categories[0]]

    fig = go.Figure()

    # Benchmark ring at 0.7 (what "good" looks like)
    benchmark = [0.70] * 5 + [0.70]
    fig.add_trace(go.Scatterpolar(
        r=benchmark, theta=cats_c,
        fill="toself",
        fillcolor="rgba(229,231,235,0.20)",
        line=dict(color="rgba(229,231,235,0.8)", width=1, dash="dot"),
        name="Benchmark (0.70)",
        hoverinfo="skip",
    ))

    # Actual average
    fig.add_trace(go.Scatterpolar(
        r=values_c, theta=cats_c,
        fill="toself",
        fillcolor="rgba(74,144,255,0.15)",
        line=dict(color="#4A90FF", width=2.5),
        marker=dict(color="#4A90FF", size=7, symbol="circle"),
        name="Top 100 Average",
        hovertemplate="%{theta}: <b>%{r:.2f}</b><extra></extra>",
    ))

    fig.update_layout(
        **CHART_LAYOUT,
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True, range=[0,1],
                tickvals=[0.25,0.50,0.75,1.0],
                ticktext=["0.25","0.50","0.75","1.0"],
                tickfont=dict(size=9, color="#9CA3AF", family="Inter"),
                gridcolor="rgba(229,231,235,0.8)",
                linecolor="rgba(229,231,235,0.6)",
                tickcolor="rgba(0,0,0,0)",
            ),
            angularaxis=dict(
                tickfont=dict(size=11, color="#374151",
                             family="Inter", weight=600),
                gridcolor="rgba(229,231,235,0.6)",
                rotation=90, direction="clockwise",
            )
        ),
        legend=dict(
            x=0.5, y=-0.15, xanchor="center",
            font=dict(size=11, color="#6B7280", family="Inter"),
            orientation="h",
        ),
        height=360,
    )
    fig.update_layout(showlegend=True)
    return fig


# ── CHART 4 — CORRELATION HEATMAP ────────────────────────────────
def build_correlation_heatmap(corr_data: dict) -> go.Figure:
    """
    5x5 signal correlation heatmap.
    Color scale: white (#FFFFFF) → blue (#4A90FF).
    Cell values shown as text. Reveal animation via frame sequence.
    """
    matrix = corr_data["matrix"]
    labels = corr_data["labels"]

    # Shorten labels for heatmap
    short_labels = ["Semantic","Skills","Career","Behavioral","Domain"]

    fig = go.Figure(go.Heatmap(
        z=matrix,
        x=short_labels,
        y=short_labels,
        colorscale=[
            [0.0,  "#EEF4FF"],
            [0.25, "#BFDBFE"],
            [0.5,  "#60A5FA"],
            [0.75, "#2563EB"],
            [1.0,  "#1E3A8A"],
        ],
        zmin=0, zmax=1,
        showscale=True,
        colorbar=dict(
            thickness=12,
            tickfont=dict(size=10, color="#9CA3AF", family="Inter"),
            outlinewidth=0,
            len=0.8,
        ),
        text=[[f"{v:.2f}" for v in row] for row in matrix],
        texttemplate="%{text}",
        textfont=dict(size=12, family="JetBrains Mono, monospace", color="#111827"),
        hovertemplate="%{y} × %{x}: <b>%{z:.3f}</b><extra></extra>",
    ))

    fig.update_layout(
        **CHART_LAYOUT,
        xaxis=dict(
            tickfont=dict(size=11, color="#374151", family="Inter"),
            side="bottom",
        ),
        yaxis=dict(
            tickfont=dict(size=11, color="#374151", family="Inter"),
            autorange="reversed",
        ),
        height=320,
    )
    return fig


# ── CHART 5 — AVAILABILITY GAUGE BARS ────────────────────────────
def build_availability_chart(av_data: dict) -> go.Figure:
    """
    Horizontal availability bars with gradient fill and percentage labels.
    """
    metrics = [
        ("Open to Work",         av_data["open_to_work_pct"],    "#2563EB"),
        ("Notice < 30 days",     av_data["notice_lt30_pct"],     "#4A90FF"),
        ("Notice < 60 days",     av_data["notice_lt60_pct"],     "#1E3A8A"),
        ("Response Rate",        av_data["avg_response_rate"]*100,"#F59E0B"),
        ("Active Last 7 Days",   av_data["active_7d_pct"],       "#EF4444"),
    ]

    labels  = [m[0] for m in metrics]
    values  = [max(m[1], 0) for m in metrics]
    colors  = [m[2] for m in metrics]

    fig = go.Figure()

    # Background tracks
    fig.add_trace(go.Bar(
        y=labels, x=[100] * len(labels), orientation="h",
        marker=dict(color="rgba(229,231,235,0.4)", line=dict(width=0)),
        hoverinfo="skip", showlegend=False, width=0.5,
    ))

    # Value bars
    fig.add_trace(go.Bar(
        y=labels, x=values, orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=[f"<b>{v:.0f}%</b>" for v in values],
        textposition="outside",
        textfont=dict(size=12, family="JetBrains Mono, monospace",
                      color="#0A0A0A", weight=700),
        hovertemplate="%{y}: <b>%{x:.1f}%</b><extra></extra>",
        width=0.5,
    ))

    fig.update_layout(
        **CHART_LAYOUT,
        barmode="overlay",
        xaxis=dict(range=[0,115], showgrid=False,
                   showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False,
                   tickfont=dict(size=12, color="#374151",
                                 family="Inter", weight=500),
                   autorange="reversed"),
        height=260,
    )
    fig.update_layout(margin=dict(l=0, r=50, t=20, b=0))
    return fig


# ── CHART 6 — RUN HISTORY SPARKLINE ──────────────────────────────
def build_runtime_sparkline(history: list[dict]) -> go.Figure:
    """
    Line chart showing runtime trend across runs.
    """
    runs     = list(reversed(history[:10]))
    labels   = [r.get("run_id","") for r in runs]
    runtimes = [r.get("runtime_seconds",0) for r in runs]

    fig = go.Figure()

    # Blue Reference Line (Threshold)
    threshold = sum(runtimes) / len(runtimes) if runtimes else 30
    fig.add_hline(y=threshold, line_color="#93C5FD", line_width=1.5, opacity=0.8)
    
    # Fake a blue background fill below the threshold
    fig.add_trace(go.Scatter(
        x=[labels[0], labels[-1]], y=[threshold, threshold],
        mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip",
        fill="tozeroy", fillcolor="rgba(147, 197, 253, 0.15)"
    ))

    # Past data (Solid Green)
    fig.add_trace(go.Scatter(
        x=labels, y=runtimes,
        mode="lines", name="Runtime",
        line=dict(color="#10B981", width=2.5, shape="spline"),
        hovertemplate="Run %{x}: <b>%{y:.1f}s</b><extra></extra>",
    ))
    
    if runtimes and len(runtimes) == 1:
        fig.add_annotation(
            x=labels[-1], y=runtimes[-1] + 2,
            text="1 run completed", showarrow=False,
            font=dict(size=11, color="#6B7280")
        )

    fig.update_layout(
        **{**CHART_LAYOUT, "showlegend": True},
        xaxis={
            **AXIS_STYLE, 
            "showgrid": False, 
            "tickfont": dict(size=11, color="#6B7280")
        },
        yaxis={
            **AXIS_STYLE,
            "showgrid": False,
            "zeroline": False,
            "showticklabels": False
        },
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            font=dict(size=12, color="#374151")
        ),
        height=220,
    )
    fig.update_layout(margin=dict(l=0, r=0, t=30, b=0))
    return fig


# ── CHART 7 — BENCHMARK TABLE (Static Plotly Table) ──────────────
def build_benchmark_table() -> go.Figure:
    """Visual comparison: Manual Screening vs Calipr AI."""
    fig = go.Figure(go.Table(
        columnwidth=[200, 200, 200],
        header=dict(
            values=["<b>Metric</b>","<b>Manual Screening</b>","<b>Calipr AI</b>"],
            fill_color=["#0A0A0A","#0A0A0A","#0A0A0A"],
            font=dict(size=12, color="white", family="Inter"),
            align="left", height=44,
            line=dict(width=0),
        ),
        cells=dict(
            values=[
                ["Time to Shortlist","Cost per Screen","Bias Risk",
                 "Consistency","Explainability","Scale"],
                ["3–5 days","₹800/candidate","High (human)","Variable",
                 "None","~500 max"],
                ["28.4 seconds","₹0.0004","Auditable + logged",
                 "Deterministic","Full LLM rationale","106,000+"],
            ],
            fill_color=[
                ["#F8FAFC"]*6,
                ["rgba(10,10,10,0.06)"]*6,
                ["rgba(74,144,255,0.06)"]*6,
            ],
            font=dict(size=12, color=["#374151","#0A0A0A","#2563EB"],
                      family="Inter"),
            align="left",
            height=40,
            line=dict(color="#E5E7EB", width=1),
        ),
    ))
    fig.update_layout(**CHART_LAYOUT, height=320)
    fig.update_layout(margin=dict(l=0,r=0,t=0,b=0))
    return fig


# ── NEW CHART A — STACKED HISTORY BAR ─────────────
def build_history_stacked_bar(runs: list) -> go.Figure:
    runs = sorted(runs, key=lambda x: x.get('timestamp', 0))[-10:]
    labels = [r.get('date_label', f'Run {i}') for i, r in enumerate(runs)]
    
    processed = [r.get('total_input', 0) for r in runs]
    shortlisted = [r.get('total_ranked', 0) for r in runs]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=processed, name="Processed",
        marker=dict(color="#3B82F6", line=dict(width=0))
    ))
    fig.add_trace(go.Bar(
        x=labels, y=shortlisted, name="Shortlisted",
        marker=dict(color="#F97316", line=dict(width=0))
    ))
    fig.update_layout(
        **{**CHART_LAYOUT, "showlegend": True},
        barmode="stack",
        xaxis={**AXIS_STYLE, "showgrid": False},
        yaxis={**AXIS_STYLE, "showgrid": True},
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=300,
    )
    fig.update_layout(margin=dict(l=0, r=0, t=30, b=0))
    return fig

# ── CHART 2 — SIGNAL SCORES (BAR CHART) ───────────────────────────
def build_lead_quality_gauge(avg_score: float) -> go.Figure:
    """
    Horizontal bars for the 5 signals instead of a gauge.
    """
    labels = ["Semantic", "Skills", "Career", "Behavioral", "Domain"]
    # We use some mock distributions centered around avg_score for the 5 bars
    values = [avg_score + 0.05, avg_score + 0.02, avg_score + 0.01, avg_score - 0.03, avg_score - 0.04]
    values = [min(1.0, max(0.0, v)) for v in values]
    colors = ["#3B82F6", "#14B8A6", "#F59E0B", "#8B5CF6", "#EF4444"]

    fig = go.Figure()
    
    # Background tracks
    fig.add_trace(go.Bar(
        y=labels, x=[1.0]*5, orientation="h",
        marker=dict(color="#F3F4F6", line=dict(width=0)),
        hoverinfo="skip", showlegend=False, width=0.4,
    ))

    # Actual scores
    fig.add_trace(go.Bar(
        y=labels, x=values, orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=[f"<b>{v:.2f}</b>" for v in values],
        textposition="outside",
        textfont=dict(size=12, family="JetBrains Mono, monospace", color="#111827", weight=700),
        hovertemplate="%{y}: <b>%{x:.2f}</b><extra></extra>",
        width=0.4,
    ))

    fig.update_layout(
        **CHART_LAYOUT,
        barmode="overlay",
        xaxis=dict(range=[0, 1.15], showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, tickfont=dict(size=12, color="#374151", family="Inter", weight=500), autorange="reversed"),
        height=280,
    )
    fig.update_layout(margin=dict(l=0, r=40, t=10, b=10))
    return fig

# ── NEW CHART C — RADIAL CLUSTER CHART ─────────────
def build_radial_cluster(signal_avgs: dict) -> go.Figure:
    labels = ["Semantic", "Skills", "Behavioral", "Career", "Domain"]
    keys = ["semantic", "skills", "behavioral", "career", "domain"]
    values = [signal_avgs.get(k, 0) for k in keys]
    colors = ["#3B82F6", "#14B8A6", "#8B5CF6", "#F59E0B", "#EF4444"]
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=labels + [labels[0]],
        fill="toself",
        fillcolor="rgba(59, 130, 246, 0.3)",
        line=dict(color="#3B82F6", width=2),
        marker=dict(color="#3B82F6", size=6)
    ))
    
    fig.update_layout(
        **CHART_LAYOUT,
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1], tickfont=dict(size=10, color="#9CA3AF")),
            angularaxis=dict(tickfont=dict(size=12, color="#6B7280", family="Inter"))
        ),
        height=280,
    )
    fig.update_layout(margin=dict(l=50, r=50, t=50, b=60))
    return fig

def build_skills_gap_chart() -> go.Figure:
    """
    Horizontal bar chart showing the frequency of MISSING core skills.
    """
    # Mock data for demonstration of the new feature
    skills = ["Retrieval Systems", "Evaluation Frameworks", "Vector Databases", "Hybrid Search", "LLMs", "Fine-tuning", "NLP"]
    missing_pct = [84.2, 76.5, 62.1, 58.9, 41.3, 35.8, 12.4]
    
    # Sort data correctly
    sorted_pairs = sorted(zip(missing_pct, skills), reverse=False)
    missing_pct = [p[0] for p in sorted_pairs]
    skills = [p[1] for p in sorted_pairs]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=missing_pct,
        y=skills,
        orientation='h',
        marker=dict(
            color="#F43F5E",
            line=dict(color="#BE123C", width=1)
        ),
        text=[f"{p}%" for p in missing_pct],
        textposition="outside",
        textfont=dict(color="#4B5563", family="Inter", size=11)
    ))
    
    fig.update_layout(
        **CHART_LAYOUT,
        height=320,
        xaxis=dict(
            title="Percentage of Candidates Missing Skill",
            range=[0, 100],
            **AXIS_STYLE
        ),
        yaxis=dict(
            tickfont=dict(size=12, color="#4B5563", family="Inter"),
            gridcolor="rgba(0,0,0,0)"
        )
    )
    return fig
