"""
AutoClean — Web UI
Run: streamlit run app.py
"""

import os
import sys
import tempfile

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autoclean.main import run_pipeline  # noqa: E402

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AutoClean",
    page_icon="🧹",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 3rem 4rem 3rem 4rem; max-width: 1100px; }

/* Header */
.ac-header { margin-bottom: 2.5rem; }
.ac-header h1 {
    font-size: 1.6rem;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.02em;
    margin: 0;
}
.ac-header p {
    color: #64748b;
    font-size: 0.875rem;
    margin-top: 0.25rem;
}

/* Upload zone */
[data-testid="stFileUploader"] {
    border: 1.5px dashed #cbd5e1 !important;
    border-radius: 10px !important;
    padding: 1.5rem !important;
    background: #f8fafc !important;
    transition: border-color 0.2s;
}
[data-testid="stFileUploader"]:hover {
    border-color: #94a3b8 !important;
}

/* Primary button */
[data-testid="stButton"] > button[kind="primary"] {
    background: #0f172a;
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 0.6rem 2rem;
    font-weight: 600;
    font-size: 0.875rem;
    letter-spacing: 0.01em;
    transition: background 0.15s;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #1e293b;
}

/* Metric cards */
[data-testid="metric-container"] {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 1rem 1.25rem;
}
[data-testid="stMetricLabel"] { font-size: 0.75rem !important; color: #64748b !important; font-weight: 500 !important; text-transform: uppercase; letter-spacing: 0.05em; }
[data-testid="stMetricValue"] { font-size: 1.5rem !important; font-weight: 700 !important; color: #0f172a !important; }
[data-testid="stMetricDelta"] { font-size: 0.8rem !important; }

/* Section labels */
.ac-section {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94a3b8;
    margin-bottom: 0.75rem;
    margin-top: 2rem;
}

/* Download buttons */
[data-testid="stDownloadButton"] > button {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    color: #0f172a;
    font-weight: 500;
    font-size: 0.85rem;
    width: 100%;
    transition: border-color 0.15s, background 0.15s;
}
[data-testid="stDownloadButton"] > button:hover {
    border-color: #94a3b8;
    background: #f8fafc;
}

/* Expander */
[data-testid="stExpander"] {
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
    background: #fff !important;
}
summary { font-size: 0.85rem !important; color: #334155 !important; font-weight: 500 !important; }

/* Divider */
hr { border: none; border-top: 1px solid #f1f5f9; margin: 1.5rem 0; }

/* Success */
[data-testid="stAlert"] { border-radius: 8px; font-size: 0.875rem; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="ac-header">
    <h1>AutoClean</h1>
    <p>Automated data profiling, cleaning, and reporting — no configuration required.</p>
</div>
""", unsafe_allow_html=True)

# ── Upload ────────────────────────────────────────────────────────────────────
uploaded = st.file_uploader(
    "Upload a CSV or Excel file to get started",
    type=["csv", "xlsx", "xls"],
    label_visibility="collapsed",
)

if not uploaded:
    st.markdown(
        "<p style='color:#94a3b8; font-size:0.85rem; margin-top:0.75rem;'>"
        "Accepts CSV, XLSX, or XLS — no configuration needed.</p>",
        unsafe_allow_html=True,
    )
    st.stop()

# ── Preview ───────────────────────────────────────────────────────────────────
ext = uploaded.name.rsplit(".", 1)[-1].lower()
preview_df = pd.read_excel(uploaded) if ext in ("xlsx", "xls") else pd.read_csv(uploaded)
uploaded.seek(0)

with st.expander(f"Preview  ·  {uploaded.name}  ({len(preview_df):,} rows × {len(preview_df.columns)} columns)", expanded=False):
    st.dataframe(preview_df.head(20), use_container_width=True, hide_index=True)

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

# ── Run ───────────────────────────────────────────────────────────────────────
_, btn_col, _ = st.columns([3, 2, 3])
with btn_col:
    run = st.button("Analyze & Clean", type="primary", use_container_width=True)

if "result" not in st.session_state:
    st.session_state.result = None

if run:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, uploaded.name)
        stem = uploaded.name.rsplit(".", 1)[0]
        output_path = os.path.join(tmpdir, f"{stem}_cleaned.csv")
        report_path = os.path.join(tmpdir, "report.json")

        with open(input_path, "wb") as f:
            f.write(uploaded.getvalue())

        with st.spinner(""):
            try:
                profile_before, profile_after, actions = run_pipeline(
                    input_path, output_path, report_path
                )
            except Exception as e:
                st.error(f"Pipeline error: {e}")
                st.stop()

        with open(output_path, "rb") as f:
            cleaned_bytes = f.read()

        md_path = report_path.replace(".json", ".md")
        html_path = report_path.replace(".json", ".html")

        st.session_state.result = {
            "profile_before": profile_before,
            "profile_after": profile_after,
            "actions": actions,
            "cleaned_bytes": cleaned_bytes,
            "report_md": open(md_path).read() if os.path.exists(md_path) else "",
            "report_html": open(html_path).read() if os.path.exists(html_path) else "",
            "filename": stem,
        }

if not st.session_state.result:
    st.stop()

res = st.session_state.result
pb = res["profile_before"]
pa = res["profile_after"]
actions = res["actions"]

st.markdown("<hr>", unsafe_allow_html=True)

# ── Metric cards ──────────────────────────────────────────────────────────────
st.markdown('<p class="ac-section">Results</p>', unsafe_allow_html=True)

def delta_fmt(key, fmt=".2f", invert=False):
    bv, av = pb.get(key), pa.get(key)
    if isinstance(bv, (int, float)) and isinstance(av, (int, float)):
        return av, format(av - bv, ("+" if (av - bv) >= 0 else "") + fmt)
    return av, None

c1, c2, c3, c4 = st.columns(4)
with c1:
    bv = pb.get("data_health_score", 0) or 0
    av = pa.get("data_health_score", 0) or 0
    st.metric("Health Score", f"{av:.1f} / 100", delta=f"{av - bv:+.1f}")
with c2:
    bv = pb.get("missing_percent", 0) or 0
    av = pa.get("missing_percent", 0) or 0
    st.metric("Missing", f"{av:.2f}%", delta=f"{av - bv:+.2f}%", delta_color="inverse")
with c3:
    bv = pb.get("duplicate_percent", 0) or 0
    av = pa.get("duplicate_percent", 0) or 0
    st.metric("Duplicates", f"{av:.2f}%", delta=f"{av - bv:+.2f}%", delta_color="inverse")
with c4:
    bv = pb.get("outlier_percent", 0) or 0
    av = pa.get("outlier_percent", 0) or 0
    st.metric("Outliers", f"{av:.2f}%", delta=f"{av - bv:+.2f}%", delta_color="inverse")

# ── Charts ────────────────────────────────────────────────────────────────────
chart_col, _ = st.columns([3, 1])

# Health score before/after
with chart_col:
    st.markdown('<p class="ac-section">Health Score</p>', unsafe_allow_html=True)
    score_b = pb.get("data_health_score") or 0
    score_a = pa.get("data_health_score") or 0

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["Before", "After"],
        y=[score_b, score_a],
        marker_color=["#cbd5e1", "#0f172a"],
        text=[f"{score_b:.1f}", f"{score_a:.1f}"],
        textposition="outside",
        textfont=dict(size=13, color="#0f172a", family="Inter"),
        width=[0.3, 0.3],
    ))
    fig.update_layout(
        yaxis=dict(range=[0, 115], showgrid=False, zeroline=False, showticklabels=False),
        xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(size=13, color="#334155", family="Inter")),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=20, b=10, l=0, r=0),
        height=220,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# Missing % by column
col_pb = pb.get("columns_profile", {})
col_pa = pa.get("columns_profile", {})
cols_missing = [
    c for c, v in col_pb.items()
    if isinstance(v.get("missing_percent"), (int, float)) and v["missing_percent"] > 0
]

if cols_missing:
    st.markdown('<p class="ac-section">Missing Values by Column</p>', unsafe_allow_html=True)
    before_vals = [col_pb[c]["missing_percent"] for c in cols_missing]
    after_vals  = [col_pa.get(c, {}).get("missing_percent", 0.0) for c in cols_missing]

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        name="Before",
        y=cols_missing, x=before_vals,
        orientation="h",
        marker_color="#cbd5e1",
    ))
    fig2.add_trace(go.Bar(
        name="After",
        y=cols_missing, x=after_vals,
        orientation="h",
        marker_color="#0f172a",
    ))
    fig2.update_layout(
        barmode="group",
        xaxis=dict(title="Missing %", showgrid=True, gridcolor="#f1f5f9", zeroline=False,
                   tickfont=dict(size=11, family="Inter")),
        yaxis=dict(showgrid=False, zeroline=False, tickfont=dict(size=11, family="Inter")),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=10, b=10, l=0, r=10),
        height=max(200, len(cols_missing) * 42),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(size=11, family="Inter"),
        ),
    )
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

# ── Actions ───────────────────────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
with st.expander(f"Cleaning log  ·  {len(actions)} actions applied", expanded=False):
    st.markdown(
        "".join(f"<p style='font-size:0.82rem;color:#334155;margin:0.2rem 0;'>"
                f"<code style='background:#f1f5f9;padding:1px 6px;border-radius:4px;"
                f"font-size:0.78rem'>{a}</code></p>" for a in actions),
        unsafe_allow_html=True,
    )

# ── Downloads ─────────────────────────────────────────────────────────────────
st.markdown('<p class="ac-section">Export</p>', unsafe_allow_html=True)
d1, d2, d3 = st.columns(3)

with d1:
    st.download_button(
        "Download Cleaned CSV",
        data=res["cleaned_bytes"],
        file_name=f"{res['filename']}_cleaned.csv",
        mime="text/csv",
        use_container_width=True,
    )
with d2:
    if res["report_html"]:
        st.download_button(
            "Download Report (HTML)",
            data=res["report_html"],
            file_name="autoclean_report.html",
            mime="text/html",
            use_container_width=True,
        )
with d3:
    if res["report_md"]:
        st.download_button(
            "Download Report (Markdown)",
            data=res["report_md"],
            file_name="autoclean_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
