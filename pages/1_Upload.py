# Page 1 — ZIP upload, file preview, triggers parsing and analysis, then routes to dashboard.

import os
import tempfile

import streamlit as st

from core.extract import extract_zip, list_zip_contents
from core.analyze import analyze


st.title("Audit Analysis Dashboard")
st.subheader("Upload your audit documents to get started")
st.write("Upload a ZIP file containing your audit documents. Supported formats: PDF, DOCX, XLSX, CSV, TXT.")

st.divider()

# ── File upload widget ────────────────────────────────────────────────────────

uploaded_file = st.file_uploader(
    label="Drop your ZIP file here or click to browse",
    type="zip",
    help="Upload a single ZIP containing all your audit documents",
)

# ── File preview ──────────────────────────────────────────────────────────────

if uploaded_file is not None:

    # Save the uploaded bytes to a temp file on disk so extract_zip can read it
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name

    # Show what's inside the ZIP before processing
    st.markdown("### Files detected in your ZIP")
    contents = list_zip_contents(tmp_path)

    if not contents:
        st.warning("The ZIP file appears to be empty.")
    else:
        for item in contents:
            icon = "✅" if item["supported"] else "❌"
            label = "" if item["supported"] else " — unsupported format (will be skipped)"
            st.write(f"{icon} **{item['name']}** ({item['size_kb']} KB){label}")

        supported_count = sum(1 for item in contents if item["supported"])
        st.caption(f"{supported_count} of {len(contents)} files will be processed.")

    st.divider()

    # ── Submit button ─────────────────────────────────────────────────────────

    if st.button("Submit & Process", type="primary", use_container_width=True):

        progress = st.progress(0, text="Starting...")
        status = st.empty()

        try:
            # Step 1 — Extract
            status.info("Extracting and parsing documents...")
            progress.progress(20, text="Parsing documents...")
            docs = extract_zip(tmp_path)

            # Step 2 — Analyze
            status.info("Sending to Gemini for analysis — this may take 15–30 seconds...")
            progress.progress(50, text="Analyzing with Gemini...")
            analysis = analyze(docs)

            # Step 3 — Save to session state
            progress.progress(90, text="Finalizing...")
            st.session_state.analysis = analysis
            st.session_state.parsed_docs = docs
            st.session_state.chat_history = []

            progress.progress(100, text="Done!")
            status.success("Analysis complete! Redirecting to dashboard...")

            # Clean up temp file
            os.unlink(tmp_path)

            # Navigate to Page 2
            st.switch_page("pages/2_Dashboard.py")

        except Exception as e:
            progress.empty()
            status.error(f"Something went wrong: {e}")
            os.unlink(tmp_path)
