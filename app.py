"""
AI-Powered Audit Analysis Dashboard — application entry point.

Streamlit multipage app. Flow: Upload -> Discover -> Deep Dive.
  - pages/1_Upload.py            : ZIP upload + parsing + Gemini analysis
  - pages/2_Dashboard.py         : KPI cards, insight panels, chat
  - pages/3_Detailed_Insights.py : document-level deep dive

This file just configures the app shell and lands the user on the upload step.
Shared state (parsed docs, the AuditAnalysis object, chat history) lives in
st.session_state so it persists as the user moves between pages.
"""

import streamlit as st

st.set_page_config(
    page_title="Audit Analysis Dashboard",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    st.title("🔍 AI-Powered Audit Analysis Dashboard")
    st.caption("Upload your audit documents, discover insights, then deep-dive.")

    st.info(
        "**Day 1 scaffold.** Project skeleton is in place. "
        "Head to the **Upload** page (left sidebar) — wiring lands over the coming days."
    )

    # TODO(week 1): initialise session_state defaults here
    #   - st.session_state.parsed_docs
    #   - st.session_state.analysis  (AuditAnalysis)
    #   - st.session_state.chat_history


if __name__ == "__main__":
    main()
