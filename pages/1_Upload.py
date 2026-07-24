# Page 1 — ZIP upload, file preview, triggers parsing and analysis, then routes to dashboard.

import os
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor

import streamlit as st

from core.extract import extract_zip, list_zip_contents
from core.analyze import analyze
from core.rag import build_index
from ui.theme import inject_css, stepper

inject_css()
stepper(active=1)   # renders into the left sidebar

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero-badge">✦&nbsp; AI-POWERED AUDIT INTELLIGENCE</div>
    <div class="hero-title">Turn audit documents into<br>
    <span class="accent">decision-ready insight.</span></div>
    <div class="hero-sub">Upload a ZIP of audit documents — reports, checklists,
    vendor records, spreadsheets — and get structured findings, risk KPIs, and a
    conversational analyst grounded in your files.</div>
    """,
    unsafe_allow_html=True,
)
st.write("")
st.markdown(
    "<div>"
    "<span class='chip'>5 file formats</span>"
    "<span class='chip'>OCR for scanned pages</span>"
    "<span class='chip'>Table-aware extraction</span>"
    "<span class='chip'>RAG-grounded chat</span>"
    "<span class='chip'>Schema-validated output</span>"
    "</div>",
    unsafe_allow_html=True,
)
st.write("")

# ── How it works ──────────────────────────────────────────────────────────────
# Hand-built cards (not Streamlit containers): gradient borders, glowing icon
# medallions, ghost step numerals, staggered entrance, hover lift.
st.markdown("### How it works")
st.markdown(
    """
<div class="hw-grid">
  <div class="hw-card" style="--d:.05s; --edge:rgba(255,230,0,.35)">
    <div class="hw-num">01</div>
    <div class="card-icon" style="--ic1:#FFE600; --ic2:#E6A700; --glow:rgba(255,230,0,.30)">📤</div>
    <div class="hw-title">Upload</div>
    <div class="hw-text">Drop a ZIP of audit documents — reports, checklists,
    spreadsheets, vendor records. Any mix of PDF, DOCX, XLSX, CSV, or TXT.</div>
  </div>
  <div class="hw-card" style="--d:.12s; --edge:rgba(151,124,255,.4)">
    <div class="hw-num">02</div>
    <div class="card-icon" style="--ic1:#977CFF; --ic2:#6C4CF0; --glow:rgba(139,108,255,.30)">🤖</div>
    <div class="hw-title">AI Analysis</div>
    <div class="hw-text">Gemini reads every document — including scanned pages via
    OCR — and extracts findings, risks, vendors, and KPIs into a validated,
    structured report.</div>
  </div>
  <div class="hw-card" style="--d:.19s; --edge:rgba(64,160,255,.4)">
    <div class="hw-num">03</div>
    <div class="card-icon" style="--ic1:#39D0FF; --ic2:#2A7FFF; --glow:rgba(64,160,255,.30)">💬</div>
    <div class="hw-title">Explore &amp; Ask</div>
    <div class="hw-text">Drill into dashboards and per-document detail, or ask the
    built-in assistant anything — every answer is grounded in your actual files.</div>
  </div>
</div>
    """,
    unsafe_allow_html=True,
)

st.write("")

# ── Where you'll end up ──────────────────────────────────────────────────────
# Colour-coded destination cards (hand-built HTML) with a styled st.page_link
# CTA beneath each. page_link navigates client-side WITHOUT a browser reload —
# a raw <a href> would reload the app and wipe session_state (the analysis).
st.markdown("### Where you'll end up")
has_analysis = st.session_state.get("analysis") is not None
_lock_html = ("<span class='dest-lock'>🔒 Unlocks after you upload documents</span>"
              if not has_analysis else "")
_locked_cls = " locked" if not has_analysis else ""

_dash_card = f"""
<div class="dest-card{_locked_cls}"
    style="--d:.05s; --edge1:rgba(255,230,0,.6); --edge2:rgba(255,180,0,.22); --halo:rgba(255,230,0,.14)">
  <div class="dest-head">
    <div class="card-icon" style="--ic1:#FFE600; --ic2:#E6A700; --glow:rgba(255,230,0,.30)">📊</div>
    <div class="dest-title">Dashboard</div>
  </div>
  <div class="dest-sub">KPI cards, risk charts, findings breakdown, vendor exposure,
  and a chat assistant for the whole audit.</div>
  {_lock_html}
</div>
"""
_detail_card = f"""
<div class="dest-card{_locked_cls}"
    style="--d:.12s; --edge1:rgba(151,124,255,.55); --edge2:rgba(56,132,255,.28); --halo:rgba(139,108,255,.14)">
  <div class="dest-head">
    <div class="card-icon" style="--ic1:#977CFF; --ic2:#6C4CF0; --glow:rgba(139,108,255,.30)">🔎</div>
    <div class="dest-title">Detailed Insights</div>
  </div>
  <div class="dest-sub">Document-by-document breakdown — tables, raw excerpts, AI
  summaries, and a chat scoped to one file at a time.</div>
  {_lock_html}
</div>
"""

d1, d2 = st.columns(2)
with d1:
    st.markdown(_dash_card, unsafe_allow_html=True)
    st.page_link("pages/2_Dashboard.py", label="Open Dashboard →",
                 disabled=not has_analysis, use_container_width=True)
with d2:
    st.markdown(_detail_card, unsafe_allow_html=True)
    st.page_link("pages/3_Detailed_Insights.py", label="Open Detailed Insights →",
                 disabled=not has_analysis, use_container_width=True)

st.divider()

# ── File upload widget ────────────────────────────────────────────────────────

st.markdown("<div class='section-band'>📁 Upload your audit documents</div>",
            unsafe_allow_html=True)
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
    try:
        contents = list_zip_contents(tmp_path)
    except zipfile.BadZipFile:
        st.error("This file isn't a valid ZIP archive — it may be corrupted or "
                 "renamed from another format. Please re-export it and try again.")
        os.unlink(tmp_path)
        st.stop()

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

        # A live pipeline panel: each stage is written as it completes, so the
        # user watches the workflow progress instead of a bare progress bar.
        try:
            with st.status("Processing your documents…", expanded=True) as status:
                st.write("📄 Parsing documents…")
                docs = extract_zip(tmp_path)
                st.write(f"✔ Parsed {len(docs)} document(s)")

                # The Gemini analysis (network-bound) and the RAG index build
                # (local CPU) are independent, so run them in parallel — the
                # indexing effectively happens for free during the Gemini wait.
                st.write("Analysing with Gemini — this may take 15–30 seconds…")
                st.write("Building the search index in parallel…")
                with ThreadPoolExecutor(max_workers=1) as pool:
                    analysis_future = pool.submit(analyze, docs)
                    index, chunks = build_index(docs)
                    st.write(f"✔ Indexed {len(chunks)} passages")
                    analysis = analysis_future.result()
                st.write(f"✔ Extracted {len(analysis.findings)} findings, "
                         f"{len(analysis.risks)} risks, {len(analysis.vendors)} vendors")

                status.update(label="Analysis complete — opening dashboard…",
                              state="complete", expanded=False)

            # Save to session state
            st.session_state.analysis = analysis
            st.session_state.parsed_docs = docs
            st.session_state.rag_index = index
            st.session_state.rag_chunks = chunks
            st.session_state.chat_history = []
            st.session_state.just_analyzed = True   # dashboard pops this to show a toast

            # Clean up temp file
            os.unlink(tmp_path)

            # Navigate to Page 2
            st.switch_page("pages/2_Dashboard.py")

        except Exception as e:
            st.error(f"Something went wrong: {e}")
            os.unlink(tmp_path)
