"""
AutoClean — Streamlit Web UI
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

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AutoClean",
    page_icon="🧹",
    layout="wide",
)

st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    h1 { margin-bottom: 0 !important; }
    .stDownloadButton > button { width: 100%; border-radius: 6px; }
    .stButton > button { border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🧹 AutoClean")
st.caption("Upload a CSV — AutoClean profiles it, fixes it, and shows you exactly what changed.")
st.divider()

# ── Upload ────────────────────────────────────────────────────────────────────
uploaded = st.file_uploader("Drop your CSV here", type=["csv"], label_visibility="collapsed")

if not uploaded:
    st.info("Upload a CSV file above to get started.")
    st.stop()

# ── Preview ───────────────────────────────────────────────────────────────────
with st.expander("Preview uploaded data", expanded=False):
    preview_df = pd.read_csv(uploaded)
    st.dataframe(preview_df.head(20), use_container_width=True)
    uploaded.seek(0)

# ── Run ───────────────────────────────────────────────────────────────────────
col_btn, _ = st.columns([1, 4])
with col_btn:
    run = st.button("Run AutoClean", type="primary", use_container_width=True)

# Store results across reruns so download buttons don't disappear
if "result_key" not in st.session_state:
    st.session_state.result_key = None

if run:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, uploaded.name)
        output_path = os.path.join(tmpdir, uploaded.name.replace(".csv", "_cleaned.csv"))
        report_path = os.path.join(tmpdir, "report.json")

        with open(input_path, "wb") as f:
            f.write(uploaded.getvalue())

        with st.spinner("Analyzing and cleaning your data…"):
            try:
                profile_before, profile_after, actions = run_pipeline(
                    input_path, output_path, report_path
                )
            except Exception as e:
                st.error(f"Pipeline failed: {e}")
                st.stop()

        # Read outputs into memory before tmpdir cleans up
        with open(output_path, "rb") as f:
            cleaned_bytes = f.read()

        md_path = report_path.replace(".json", ".md")
        report_md = ""
        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                report_md = f.read()

        html_path = report_path.replace(".json", ".html")
        report_html = ""
        if os.path.exists(html_path):
            with open(html_path, "r", encoding="utf-8") as f:
                report_html = f.read()

    st.session_state.result_key = {
        "profile_before": profile_before,
        "profile_after": profile_after,
        "actions": actions,
        "cleaned_bytes": cleaned_bytes,
        "report_md": report_md,
        "report_html": report_html,
        "filename": uploaded.name,
    }

if not st.session_state.result_key:
    st.stop()

res = st.session_state.result_key
profile_before = res["profile_before"]
profile_after = res["profile_after"]
actions = res["actions"]

st.success("Cleaning complete!")
st.divider()

# ── Health Score + Metrics ────────────────────────────────────────────────────
score_before = profile_before.get("data_health_score") or 0.0
score_after = profile_after.get("data_health_score") or 0.0

col_chart, col_metrics = st.columns([1, 2], gap="large")

with col_chart:
    st.subheader("Health Score")
    fig_score = go.Figure(go.Bar(
        x=["Before", "After"],
        y=[score_before, score_after],
        marker_color=["#e05252", "#2ecc71"],
        text=[f"{score_before:.1f}", f"{score_after:.1f}"],
        textposition="outside",
        width=[0.35, 0.35],
    ))
    fig_score.update_layout(
        yaxis=dict(range=[0, 115], showgrid=True, gridcolor="#f0f0f0", title="Score / 100"),
        xaxis=dict(showgrid=False),
        plot_bgcolor="white",
        margin=dict(t=10, b=10, l=10, r=10),
        height=280,
        showlegend=False,
    )
    st.plotly_chart(fig_score, use_container_width=True)

with col_metrics:
    st.subheader("Summary")
    metric_defs = [
        ("Rows",         "rows",              "{:.0f}"),
        ("Missing %",    "missing_percent",   "{:.2f}%"),
        ("Duplicate %",  "duplicate_percent", "{:.2f}%"),
        ("Outlier %",    "outlier_percent",   "{:.2f}%"),
        ("Health Score", "data_health_score", "{:.1f}"),
    ]
    rows_data = []
    for label, key, fmt in metric_defs:
        bv = profile_before.get(key)
        av = profile_after.get(key)
        if isinstance(bv, (int, float)) and isinstance(av, (int, float)):
            delta = av - bv
            rows_data.append({
                "Metric": label,
                "Before": fmt.format(bv),
                "After": fmt.format(av),
                "Δ": ("+" if delta > 0 else "") + fmt.format(delta),
            })
    st.dataframe(
        pd.DataFrame(rows_data).set_index("Metric"),
        use_container_width=True,
        height=210,
    )

st.divider()

# ── Missing Values by Column ──────────────────────────────────────────────────
col_profiles_before = profile_before.get("columns_profile", {})
col_profiles_after = profile_after.get("columns_profile", {})

cols_with_missing = [
    c for c, v in col_profiles_before.items()
    if isinstance(v.get("missing_percent"), (int, float)) and v["missing_percent"] > 0
]

if cols_with_missing:
    st.subheader("Missing Values by Column")
    before_vals = [col_profiles_before[c]["missing_percent"] for c in cols_with_missing]
    after_vals  = [col_profiles_after.get(c, {}).get("missing_percent", 0.0) for c in cols_with_missing]

    fig_missing = go.Figure()
    fig_missing.add_trace(go.Bar(
        name="Before",
        y=cols_with_missing,
        x=before_vals,
        orientation="h",
        marker_color="#e05252",
    ))
    fig_missing.add_trace(go.Bar(
        name="After",
        y=cols_with_missing,
        x=after_vals,
        orientation="h",
        marker_color="#2ecc71",
    ))
    fig_missing.update_layout(
        barmode="group",
        xaxis=dict(title="Missing %", showgrid=True, gridcolor="#f0f0f0"),
        yaxis=dict(showgrid=False),
        plot_bgcolor="white",
        margin=dict(t=10, b=10, l=10, r=10),
        height=max(260, len(cols_with_missing) * 45),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_missing, use_container_width=True)
    st.divider()

# ── Cleaning Actions ──────────────────────────────────────────────────────────
with st.expander(f"Cleaning Actions ({len(actions)})", expanded=False):
    for action in actions:
        st.markdown(f"- `{action}`")

st.divider()

# ── Downloads ─────────────────────────────────────────────────────────────────
st.subheader("Download")
dl1, dl2, dl3 = st.columns(3)

stem = res["filename"].removesuffix(".csv")

with dl1:
    st.download_button(
        label="Cleaned CSV",
        data=res["cleaned_bytes"],
        file_name=f"{stem}_cleaned.csv",
        mime="text/csv",
        use_container_width=True,
    )

with dl2:
    if res["report_html"]:
        st.download_button(
            label="Report (HTML)",
            data=res["report_html"],
            file_name="autoclean_report.html",
            mime="text/html",
            use_container_width=True,
        )

with dl3:
    if res["report_md"]:
        st.download_button(
            label="Report (Markdown)",
            data=res["report_md"],
            file_name="autoclean_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
