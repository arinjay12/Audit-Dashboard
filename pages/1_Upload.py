"""
Page 1 — File Upload.

Drag-and-drop a single ZIP of audit documents (PDF/DOCX/XLSX/CSV/TXT).
Steps: upload -> list detected files for confirmation -> "Submit & Process"
-> parse (core.extract) -> analyze (core.analyze) with a progress indicator
-> store results in session_state -> navigate to the Dashboard.

TODO(week 3): build the upload UI; wiring to extract/analyze lands earlier.
"""

import streamlit as st

st.header("📤 Upload Audit Documents")
st.write("Placeholder — Day 1 scaffold. ZIP upload + parsing pipeline coming this week.")
