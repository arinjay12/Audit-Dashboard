"""
Page 2 — Main Dashboard.

Reads the AuditAnalysis object from session_state and renders:
  A. KPI cards (clickable -> AI insight panel + follow-up chat)
  B. Insight panels (risk heatmap, findings breakdown, trends, recommendations)
  C. Persistent contextual chat window

All rendering is deterministic (no LLM in the render path); only the
click-to-explain panels and chat call Gemini on demand.

TODO(week 3-4).
"""

import streamlit as st

st.header("📊 Audit Dashboard")
st.write("Placeholder — Day 1 scaffold.")
