# Page 2 — the executive dashboard. Reads the validated AuditAnalysis from
# session state and renders KPI cards, charts, insight panels, and the chat
# assistant. All rendering is delegated to the ui/ components.

import streamlit as st

from ui.kpi_cards import render_kpi_cards
from ui.charts import (
    severity_donut, status_bar, category_bar, risk_heatmap, compliance_gauge,
)
from ui.panels import (
    render_findings, render_vendors, render_discrepancies, render_recommendations,
)
from ui.chat_panel import render_chat_panel
from ui.insight_dialog import open_insight
from ui.theme import inject_css, stepper, section_header

inject_css()


# ── Guard: nothing to show until documents have been processed ────────────────
analysis = st.session_state.get("analysis")
if analysis is None:
    st.title("Dashboard")
    st.info("No analysis yet. Upload your audit documents to get started.")
    if st.button("Go to Upload", type="primary"):
        st.switch_page("pages/1_Upload.py")
    st.stop()


# One-shot toast when arriving fresh from the upload pipeline.
if st.session_state.pop("just_analyzed", False):
    st.toast(f"Extracted {len(analysis.findings)} findings from "
             f"{len(st.session_state.parsed_docs)} document(s)", icon="✅")


# ── Header ────────────────────────────────────────────────────────────────────
st.title("Audit Dashboard")
stepper(active=2)
st.write("")
st.markdown(
    f"<div class='exec-banner'><b>Executive Summary</b><br>{analysis.overall_summary}</div>",
    unsafe_allow_html=True,
)
st.write("")


# ── KPI cards ─────────────────────────────────────────────────────────────────
section_header("⚡", "Key Metrics", "#FFE600")
render_kpi_cards(analysis)
st.divider()


# ── Charts ────────────────────────────────────────────────────────────────────
# No border containers here: the charts themselves are styled as glass cards
# (via stPlotlyChart CSS), which renders reliably across Streamlit versions.
section_header("📈", "Risk & Compliance Analytics", "#39A0FF")
row1_left, row1_right = st.columns([1, 1])
with row1_left:
    st.plotly_chart(severity_donut(analysis.findings), use_container_width=True)
with row1_right:
    st.plotly_chart(status_bar(analysis.findings), use_container_width=True)

row2_left, row2_right = st.columns([1, 1])
with row2_left:
    st.plotly_chart(risk_heatmap(analysis), use_container_width=True)
    if st.button("💬 Discuss Risk Summary", key="discuss_risk", use_container_width=True):
        open_insight("Risk Summary")
with row2_right:
    st.plotly_chart(category_bar(analysis.findings), use_container_width=True)

st.plotly_chart(compliance_gauge(analysis), use_container_width=True)
st.divider()


# ── Insight panels ────────────────────────────────────────────────────────────
render_findings(analysis)
st.divider()

left, right = st.columns([1, 1])
with left:
    render_vendors(analysis)
with right:
    render_discrepancies(analysis)

st.divider()
render_recommendations(analysis)


# ── Chat assistant (collapsible, bottom of page) ──────────────────────────────
render_chat_panel()
