# Entry point — sets up the Streamlit app config and shared session state used across all three pages.

import streamlit as st

st.set_page_config(
    page_title="Audit Analysis Dashboard",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialise session state keys used across all pages.
# These are set once here so every page can safely read them without checking if they exist.
if "analysis" not in st.session_state:
    st.session_state.analysis = None          # AuditAnalysis object, populated after processing

if "parsed_docs" not in st.session_state:
    st.session_state.parsed_docs = []         # list of ParsedDoc objects

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []        # list of {role, content} dicts for the chat window

# Land the user on the upload page
st.switch_page("pages/1_Upload.py")
