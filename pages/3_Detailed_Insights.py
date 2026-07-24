# Page 3 — Detailed Insights. A document-by-document breakdown: pick one file
# and see its metadata, the findings attributed to it, and its financial
# discrepancies. Reuses the dashboard's components and the same shared chat.
#
# (First part: document picker + per-document findings/discrepancies. Tables,
#  raw excerpts, and click-to-explain come next.)

import re

import pandas as pd
import streamlit as st

from core.chat import summarize_document
from ui.panels import render_finding_list
from ui.chat_panel import render_chat_panel
from ui.charts import severity_donut, status_bar, category_bar
from ui.kpi_cards import render_mini_kpis
from ui.theme import MUTED, ACCENT, SEVERITY_COLORS, inject_css, stepper, section_header

inject_css()


# ── Guard: nothing to show until documents have been processed ────────────────
analysis = st.session_state.get("analysis")
if analysis is None:
    st.title("Detailed Insights")
    st.info("No analysis yet. Upload your audit documents to get started.")
    if st.button("Go to Upload", type="primary"):
        st.switch_page("pages/1_Upload.py")
    st.stop()


st.title("Detailed Insights")
stepper(active=3)
st.caption("A document-by-document breakdown of the audit.")

parsed_docs = st.session_state.get("parsed_docs", [])

# Build the list of documents to browse. Prefer the actual uploaded files
# (parsed_docs); if those aren't in session (e.g. a cached preview), fall back
# to whichever documents the analysis attributes findings/discrepancies to.
if parsed_docs:
    doc_names = [d.filename for d in parsed_docs]
else:
    doc_names = sorted(
        {f.source_doc for f in analysis.findings}
        | {d.source_doc for d in analysis.discrepancies}
    )

if not doc_names:
    st.info("No documents to display.")
    st.stop()

selected = st.selectbox("Select a document", doc_names)

doc = next((d for d in parsed_docs if d.filename == selected), None)

# ── Mini KPI strip for this document ──────────────────────────────────────────
# Small non-clickable rectangles (unlike Page 2's big cards) — a quick read of
# the selected document's numbers. Computed once here, reused further down.
doc_findings = [f for f in analysis.findings if f.source_doc == selected]
doc_disc = [d for d in analysis.discrepancies if d.source_doc == selected]
sev_counts = {s: sum(1 for f in doc_findings if f.severity == s)
              for s in ("High", "Medium", "Low")}
pending_count = sum(1 for f in doc_findings if f.status in ("Open", "In Progress"))

mini = [
    ("Findings", len(doc_findings), ACCENT),
    ("High", sev_counts["High"], SEVERITY_COLORS["High"]),
    ("Medium", sev_counts["Medium"], SEVERITY_COLORS["Medium"]),
    ("Low", sev_counts["Low"], SEVERITY_COLORS["Low"]),
    ("Pending", pending_count, SEVERITY_COLORS["Medium"]),
    ("Discrepancies", len(doc_disc), SEVERITY_COLORS["High"]),
]
if doc:
    mini.append(("Pages", doc.page_count or "—", MUTED))
    mini.append(("Tables", len(doc.tables), MUTED))
render_mini_kpis(mini)

# ── AI summary of the selected document (generated on demand, cached) ─────────
# The first time a document is selected we call Gemini for a summary; it's cached
# per document in session state, so re-selecting it is instant and costs nothing.
summaries = st.session_state.setdefault("doc_summaries", {})
if selected not in summaries:
    with st.spinner("Summarising this document…"):
        try:
            summaries[selected] = summarize_document(
                selected, analysis, raw_text=(doc.raw_text if doc else None))
            st.toast("Document summary ready", icon="📄")
        except Exception as e:
            summaries[selected] = f"_Could not generate summary: {e}_"

section_header("📄", "Document summary", "#977CFF")
with st.container(border=True):
    st.markdown(summaries[selected])

st.divider()

# ── Findings attributed to this document ──────────────────────────────────────
section_header("📋", "Findings in this document", "#FF6B81", note=f"{len(doc_findings)}")
if doc_findings:
    render_finding_list(doc_findings)
else:
    st.markdown(f"<span style='color:{MUTED}'>No findings were attributed to this document.</span>",
                unsafe_allow_html=True)

# ── Requestable chart for this document's findings ────────────────────────────
# Only findings-based charts can be scoped to a single document (findings carry a
# source_doc; risks/compliance are audit-wide), so we offer those three.
if doc_findings:
    st.divider()
    section_header("📊", "Visualise these findings", "#39A0FF")
    choice = st.segmented_control(
        "Chart", ["By severity", "By status", "By category"],
        label_visibility="collapsed",
        key=f"chart_choice::{selected}",
    )
    if choice == "By severity":
        st.plotly_chart(severity_donut(doc_findings), use_container_width=True)
    elif choice == "By status":
        st.plotly_chart(status_bar(doc_findings), use_container_width=True)
    elif choice == "By category":
        st.plotly_chart(category_bar(doc_findings), use_container_width=True)

# ── Financial discrepancies attributed to this document ───────────────────────
if doc_disc:
    st.divider()
    section_header("💸", "Financial discrepancies in this document", "#FFB020",
                   note=f"{len(doc_disc)}")
    for d in doc_disc:
        amount = f"${d.amount:,.2f}" if d.amount is not None else "—"
        st.markdown(f"**{amount}** &nbsp; {d.description}")

# ── Tables extracted from this document ───────────────────────────────────────
# doc.tables is a list of {source, headers, rows} dicts produced by extract.py.
# Collapsed by default — a large PDF can have many tables, and leaving them open
# buries the chat under a lot of scrolling.
if doc and doc.tables:
    st.divider()
    def _tidy_table(headers, rows):
        """
        Clean up PyMuPDF's table detection artefacts for display:

        1. Placeholder headers. "Col0"/"0"-style names mean no header row was
           detected. If ALL headers are placeholders, the first data row is the
           real header; if only SOME are (the rest being captured content),
           demote the whole header row back into the data and use generic names.
        2. Fragmented rows. Borderless tables often come back as line soup —
           each wrapped line its own row, with the other column empty. When most
           rows have at most one filled cell, stitch fragments back together:
           a row with BOTH its first and last cells filled starts a new logical
           row; everything else appends into the current one, column-wise.
        """
        headers = [str(h).strip() for h in (headers or [])]
        rows = [[str(c).strip() for c in r] for r in (rows or [])]
        ncols = max([len(headers)] + [len(r) for r in rows], default=0)
        if ncols == 0:
            return headers, rows
        headers = headers + [""] * (ncols - len(headers))
        rows = [r + [""] * (ncols - len(r)) for r in rows]

        def is_placeholder(h):
            return h == "" or re.fullmatch(r"(Col)?\d+", h) is not None

        ph = [is_placeholder(h) for h in headers]
        if all(ph) and len(rows) > 1:
            headers, rows = rows[0], rows[1:]
            headers = [h or f"Column {j + 1}" for j, h in enumerate(headers)]
        elif any(ph):
            content = ["" if is_placeholder(h) else h for h in headers]
            if any(content):
                rows = [content] + rows
            headers = [f"Column {j + 1}" for j in range(ncols)]

        filled = lambda r: sum(1 for c in r if c)
        if ncols >= 2 and rows and sum(1 for r in rows if filled(r) <= 1) / len(rows) >= 0.6:
            stitched, cur = [], None
            for r in rows:
                if cur is None or (r[0] and r[-1]):
                    if cur is not None:
                        stitched.append(cur)
                    cur = list(r)
                else:
                    for j, c in enumerate(r):
                        if c:
                            cur[j] = (cur[j] + " " + c).strip()
            if cur is not None:
                stitched.append(cur)
            rows = stitched
        return headers, rows

    with st.expander(f"Tables extracted from this document ({len(doc.tables)})", expanded=False):
        for i, t in enumerate(doc.tables, 1):
            st.caption(t.get("source", f"Table {i}"))
            headers, rows = _tidy_table(t.get("headers"), t.get("rows"))
            try:
                df = pd.DataFrame(rows, columns=headers or None)
                st.dataframe(df, use_container_width=True, hide_index=True)
            except Exception:
                # Fall back to a plain render if the table shape is irregular.
                st.write(headers)
                st.write(rows)

# ── Raw extracted text (transparency: what the pipeline actually read) ─────────
doc_chunks = [c for c in st.session_state.get("rag_chunks", []) if c.get("source") == selected]
if doc_chunks:
    st.divider()
    with st.expander(f"Raw extracted text — {len(doc_chunks)} excerpt(s)", expanded=False):
        for c in doc_chunks:
            pages = c.get("pages")
            if pages and pages[0] != pages[1]:
                st.markdown(f"**Pages {pages[0]}–{pages[1]}**")
            elif pages:
                st.markdown(f"**Page {pages[0]}**")
            st.text(c["text"])
            st.divider()

# ── Document-scoped chat assistant ────────────────────────────────────────────
# Unlike Page 2's global chat, this one only answers about the selected document
# and keeps its own conversation per file.
st.divider()
render_chat_panel(document=selected)
