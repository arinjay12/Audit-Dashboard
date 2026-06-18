# Audit Analysis Dashboard

An AI-powered web application where users upload audit documents and receive structured insights, KPIs, and conversational analytics.

---

## Approach

The application is built around a schema-first pipeline:

1. User uploads a ZIP of audit documents (PDF, DOCX, XLSX, CSV, TXT)
2. Documents are parsed into plain text and tables — no AI involved at this stage
3. A single Gemini call reads all extracted text and populates a structured `AuditAnalysis` object containing findings, risks, compliance scores, vendor ratings, and KPI roll-ups
4. The dashboard renders entirely from that saved object — no LLM in the render path
5. Gemini is only called again when the user clicks a KPI card for a deeper explanation or types in the chat window

This keeps the dashboard fast and consistent across all three pages.

---

## Application Structure

Three pages, one flow: **Upload → Discover → Deep Dive**

- **Page 1 — Upload:** ZIP file upload, file list preview, processing with progress indicator
- **Page 2 — Dashboard:** KPI cards, insight panels (risk heatmap, findings breakdown, recommendations), persistent chat
- **Page 3 — Detailed Insights:** Document-level breakdown, clause-level flags, inline charts, same chat capability

---

## Tech Stack

| Layer | Tool |
|---|---|
| Frontend & Backend | Streamlit |
| LLM | Google Gemini 2.5 Flash |
| PDF parsing | PyMuPDF |
| DOCX parsing | python-docx |
| XLSX / CSV parsing | pandas |
| Charts | Plotly |
| Schema validation | Pydantic |

---

## Project Layout

```
app.py                        # entry point, page routing, session state
pages/
  1_Upload.py                 # ZIP upload + processing
  2_Dashboard.py              # KPI cards, panels, chat
  3_Detailed_Insights.py      # document-level deep dive
core/
  extract.py                  # ZIP → text/tables (no LLM)
  schema.py                   # ParsedDoc + AuditAnalysis data models
  analyze.py                  # text → AuditAnalysis via Gemini
  gemini_client.py            # Gemini API wrapper
  chat.py                     # contextual chat + click-to-explain
ui/
  kpi_cards.py
  panels.py
  charts.py
.streamlit/
  config.toml                 # dark theme
  secrets.toml.example        # API key template (real key is gitignored)
```

---

## Setup

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# add your Gemini API key to secrets.toml
streamlit run app.py
```

---

## Progress

**Day 1 (17 Jun):** Project scaffolded — folder structure, dependencies, Streamlit dark theme config, secrets handling, module stubs, git initialised.

**Day 2 (18 Jun):** Gemini client written and tested (`gemini_client.py`). Document parsing pipeline built (`extract.py`) covering all 5 formats. `ParsedDoc` data model defined (`schema.py`). Parser tested against a real file and working.
