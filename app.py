# Entry point — sets up the app config, shared session state, and navigation.
#
# Navigation uses st.navigation with position="top": the three pages render as a
# tab-style bar across the top instead of the default sidebar list (which also
# showed this entry script itself as an "app" page). This file runs on every
# rerun BEFORE the selected page, so the session-state init here is guaranteed
# to happen for all pages.

import streamlit as st

st.set_page_config(
    page_title="Audit Analysis Dashboard",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",   # the sidebar hosts the workflow stepper panel
)

# EY mark in the app header (top-left, next to the nav tabs, on every page).
# SVG recreated for dark backgrounds: yellow beam over light letters.
st.logo("assets/ey_logo.svg", size="large")

# Initialise session state keys used across all pages.
# These are set once here so every page can safely read them without checking if they exist.
if "analysis" not in st.session_state:
    st.session_state.analysis = None          # AuditAnalysis object, populated after processing

if "parsed_docs" not in st.session_state:
    st.session_state.parsed_docs = []         # list of ParsedDoc objects

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []        # list of {role, content} dicts for the chat window

if "rag_index" not in st.session_state:
    st.session_state.rag_index = None         # FAISS index for chat retrieval

if "rag_chunks" not in st.session_state:
    st.session_state.rag_chunks = []          # chunk metadata list paired with the index

# ── Pages (top tab bar) ───────────────────────────────────────────────────────
pg = st.navigation(
    [
        st.Page("pages/1_Upload.py", title="Upload", icon="📤", url_path="upload", default=True),
        st.Page("pages/2_Dashboard.py", title="Dashboard", icon="📊", url_path="dashboard"),
        st.Page("pages/3_Detailed_Insights.py", title="Detailed Insights", icon="🔎", url_path="insights"),
    ],
    position="top",
)
pg.run()
