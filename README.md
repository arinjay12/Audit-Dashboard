# Audit Analysis Dashboard

An AI-powered web application that turns a folder of audit documents into a structured, interactive audit report — findings, risks, vendor exposure, KPIs, and a document-grounded conversational assistant.

Upload a ZIP of audit documents → get a validated, structured analysis → explore it through dashboards, per-document drill-downs, and chat.

---

## What it does

- **Ingests mixed document sets** — PDF, DOCX, XLSX, CSV, TXT in any combination, including scanned/image-based PDF pages (OCR'd automatically) and embedded tables (extracted as structured data, not garbled text).
- **Produces a structured audit analysis** in one Gemini call: findings (with severity/status/category/recommendation), risks (likelihood × impact), vendor risk ratings, financial discrepancies, compliance scoring, and derived KPIs — all schema-validated so the dashboard can never show numbers that contradict the underlying data.
- **Executive dashboard** — KPI cards, severity/status/category charts, a risk heatmap, a compliance gauge, and click-to-explain AI insight popups on every metric and panel.
- **Document-level deep dive** — pick any single uploaded file and get an AI-generated summary, its own findings/discrepancies, extracted tables, raw excerpts, requestable charts, and a chat assistant scoped to *only* that document.
- **Grounded conversational assistant** — powered by retrieval-augmented generation (RAG) over the actual document text, so answers cite real pages and sources instead of guessing. Depth of answer scales with the question asked.
- **Built for reliability, not just a demo** — API key rotation, retry/backoff on transient errors, JSON-repair on malformed model output, defensive schema normalizers, and guards against empty/corrupt uploads.

---

## Approach

The application is built around a **schema-first pipeline**, with the AI touched exactly twice per upload:

1. User uploads a ZIP of audit documents.
2. Documents are parsed into plain text and tables — OCR runs on scanned pages, tables are extracted as structured data. No AI involved at this stage.
3. All extracted text is chunked and embedded locally (no API cost) into a FAISS index, powering retrieval for chat later.
4. **One Gemini call** reads all extracted text and returns a structured `AuditAnalysis` object — findings, risks, vendors, discrepancies, compliance, KPIs, recommendations — validated against a Pydantic schema before anything renders.
5. The dashboard renders entirely from that saved object — no LLM in the render path, so it's instant and consistent.
6. Gemini is called again only on demand: when the user asks the chat assistant something, clicks a KPI card for a deeper explanation, or requests a document summary — each of those grounded in the RAG index and/or the structured analysis, never re-reading the raw documents from scratch.

---

## Application Structure

Three pages, one flow: **Upload → Discover → Deep Dive**

- **Page 1 — Upload:** drag-and-drop ZIP upload, file preview, a live pipeline status panel during processing (parse → index → analyze).
- **Page 2 — Dashboard:** KPI cards, risk/compliance charts, findings/vendor/discrepancy/recommendation panels with severity filters, click-to-explain AI insights, a collapsible chat assistant.
- **Page 3 — Detailed Insights:** per-document picker, an AI-generated document summary, that document's findings/discrepancies/tables/raw excerpts, requestable charts, and a chat scoped to just that document.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Frontend & Backend | Streamlit |
| LLM | Google Gemini (2.5 Flash) |
| PDF parsing | PyMuPDF |
| DOCX parsing | python-docx |
| XLSX / CSV parsing | pandas |
| OCR (scanned pages) | Tesseract via pytesseract |
| RAG embeddings | sentence-transformers (`all-MiniLM-L6-v2`, local) |
| Vector search | FAISS |
| Charts | Plotly |
| Schema validation | Pydantic |

---

## Project Layout

```
app.py                        # entry point: top nav, EY branding, session state
pages/
  1_Upload.py                 # ZIP upload, live processing pipeline
  2_Dashboard.py              # KPI cards, charts, panels, chat
  3_Detailed_Insights.py      # per-document deep dive
core/
  extract.py                  # ZIP -> text/tables/OCR (no LLM)
  schema.py                   # ParsedDoc + AuditAnalysis data models (validated)
  analyze.py                  # extracted text -> AuditAnalysis via Gemini
  chat.py                     # chat, click-to-explain, document summaries
  rag.py                      # chunking, embedding, retrieval (FAISS)
  gemini_client.py            # Gemini API wrapper (key rotation, retry/backoff)
ui/
  theme.py                    # palette, global CSS, section headers, stepper
  kpi_cards.py                # KPI cards + mini-KPI strip
  charts.py                   # Plotly chart builders
  panels.py                   # findings/vendors/discrepancies/recommendations
  chat_panel.py                # persistent chat widget
  insight_dialog.py           # click-to-explain modal
assets/
  ey_logo.svg
.streamlit/
  config.toml                 # dark theme
  secrets.toml.example        # API key template (real key is gitignored)
```

---

## Setup

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# add your Gemini API key(s) to secrets.toml — a second key is optional but
# recommended, since the client automatically rotates to it on quota limits
streamlit run app.py
```

**OCR requires Tesseract to be installed separately** (not a pip package): [Tesseract-OCR](https://github.com/tesseract-ocr/tesseract) must be on your system PATH, or its install path set in `core/extract.py`. Everything else works without it — OCR only kicks in for scanned/image PDF pages.

The first run downloads a local embedding model (~80MB, one-time, no API cost).

---

## Demo / Test Scripts

A few standalone scripts exist for verifying specific parts of the pipeline without running the full app:

- `test_chat.py` — cached end-to-end chat test (loads instantly after the first run)
- `test_chat_multi.py` — same, with a multi-document upload
- `test_ocr_page7.py` — OCR accuracy demo on a scanned page
- `test_table_extract.py` — shows raw vs. structured table extraction
- `rebuild_index_only.py` — rebuilds the RAG index without a Gemini call
