# Audit Analysis Dashboard — Project Context

Internship project (EY). AI-powered dashboard that takes a ZIP of audit documents
(PDF, DOCX, XLSX, CSV, TXT) and produces structured findings, KPIs, and a
conversational Q&A assistant, powered by Google Gemini (`gemini-2.5-flash`).

**Deadline:** July 15, 2026.
**Pages:** Upload → Dashboard → Detailed Insights (3-page Streamlit app).

---

## Architecture

Two distinct passes over the documents, used for two different jobs:

1. **Analysis pass** (`core/analyze.py`) — every document's full extracted text is
   concatenated and sent to Gemini in **one call**, with a detailed rubric prompt
   (role, extraction guide, rating rubrics, KPI derivation math, anti-hallucination
   rules). Returns one JSON object, validated into a Pydantic `AuditAnalysis`
   object (findings, risks, vendors, discrepancies, compliance, KPIs,
   recommendations). Runs once per upload.

2. **Chat / RAG** (`core/chat.py` + `core/rag.py`) — instead of re-sending the full
   document set on every message, documents are chunked (~400 words, 50 overlap),
   embedded locally with `sentence-transformers` (`all-MiniLM-L6-v2`, free, no
   Gemini cost), and indexed in FAISS once at upload time. Every chat message
   retrieves the ~20 most relevant chunks (semantic search + explicit/inferred
   page lookup) and combines them with the structured summary and recent
   conversation history.

**Pipeline:** ZIP → `extract.py` (parse + OCR + table extraction) → `analyze.py`
(Gemini call → validated schema) + `rag.py` (chunk/embed/index, in parallel) →
dashboard renders from the validated object; chat answers from summary + RAG.

---

## What's done

- **Extraction** (`core/extract.py`): PDF/DOCX/XLSX/CSV/TXT parsing. PDFs get
  page markers (`[Page N]`) and table markers (`[TABLE ...] Columns: ... Row N:`).
  Scanned/image pages OCR'd at 300 DPI, dual-pass (psm 3 for reading order + psm
  11 sparse mode to catch stray text like a date next to a logo), merged.
- **Gemini client** (`core/gemini_client.py`): key rotation across multiple API
  keys (429 quota → rotate key), retry with exponential backoff (503 → retry
  same key), and automatic regeneration if a JSON response comes back malformed
  (rare token-level slip on long outputs, not a prompt bug).
- **Analysis prompt** (`core/analyze.py`): rewritten from a 3-line prompt to a
  full rubric (severity/status/likelihood/impact/vendor-risk definitions,
  explicit KPI derivation so numbers tie out, instructions to normalize a
  source document's own wording — e.g. "Partially Implemented" — to the allowed
  enum values rather than copying it verbatim).
- **Schema** (`core/schema.py`): Pydantic validation on every Gemini field;
  defensive normalizers for `Vendor.risk_rating` and `Finding.status` so an
  unexpected value from the model gets mapped to the closest allowed value
  instead of crashing validation.
- **RAG** (`core/rag.py`): page-aware chunking (fixed a bug where `[Page 7]`'s
  space broke the tracking regex — all chunks were mislabelled page 1), direct
  page lookup for "what does page N say" questions, and page-hint detection that
  also scans the assistant's *previous* reply for cited pages (`(p.7, ...)`) so
  a bare follow-up like "when was it signed?" still resolves correctly.
  `top_k` widened from 8 → 20 chunks per query after finding a relevant chunk
  can rank surprisingly low semantically when its embedding is diluted by
  unrelated surrounding content (e.g. a date glued onto an unrelated table).
- **Chat prompt** (`core/chat.py`): rewritten with the same rubric-style detail —
  explicit rules for grounding, exact dates/figures, citing page/source, and
  refusing to fill gaps with assumptions.
- **Multi-document validation**: confirmed the pipeline handles a PDF + multiple
  Excel files zipped together, with correct per-finding `source_doc` attribution
  across formats and cross-document Q&A.
- **Test data**: 2 fabricated Excel files (vendor risk assessment, findings log)
  with realistic mock data, plus one real public PDF audit report
  (UT Southwestern FY2024 Annual Internal Audit Report) used as the primary demo doc.
- **Page 2 — Dashboard** (`pages/2_Dashboard.py`): built. Executive summary
  banner, 8 KPI cards, five Plotly charts (severity donut, remediation-status
  bar, risk matrix/heatmap, category stacked bar, compliance gauge), findings
  list (expandable, sorted High→Low, severity/status badges), vendors +
  discrepancies columns, priority recommendations, and the chat assistant.
  Rendering is split into reusable `ui/` components: `theme.py` (shared palette),
  `kpi_cards.py`, `charts.py`, `panels.py`, `chat_panel.py`.
- **Click-to-explain (spec Section A & B)**: every KPI card has an "AI Insight"
  button and every insight panel (Findings, Vendors, Discrepancies,
  Recommendations, Risk Summary) has a "Discuss" button. Clicking opens an
  `st.dialog` modal (`ui/insight_dialog.py`) with a detailed, grounded AI insight
  for that item (via the rewritten `explain()` prompt) plus a follow-up chat
  scoped to that topic (grounded via RAG through `chat()`). The initial insight
  is cached per topic so the modal's own reruns don't re-hit Gemini. Verified
  end-to-end in the running app (open → insight → follow-up → close).
- **RAG wired into the real app**: `1_Upload.py` now calls `build_index()` and
  stores `rag_index` / `rag_chunks` in `session_state` (added to `app.py` init),
  so the dashboard chat uses retrieval — previously RAG only existed in the
  terminal test scripts. Verified end-to-end in the running app.
- **Demo/test scripts** (repo root): `test_chat.py` (single-PDF chat, cached),
  `test_chat_multi.py` (PDF + Excel combined, cached separately in
  `.cache_multi/`), `test_ocr_page7.py` (OCR accuracy demo on a scanned letter),
  `test_table_extract.py` (shows raw table → labelled form fed to Gemini),
  `rebuild_index_only.py` (rebuilds RAG index without a Gemini call, for
  chunking-only changes).

---

## What's pending

- **Page 3 — Detailed Insights** (`pages/3_Detailed_Insights.py`, currently a
  stub): not started. Intended as a per-document, more granular drill-down
  (tables, raw excerpts, per-file findings) vs Page 2's executive view.
- Push recent changes to GitHub (not yet done this round).

---

## Known gotchas worth remembering

- The `.cache/` and `.cache_multi/` folders let test scripts skip the Gemini
  call entirely on repeat runs — use `--rebuild` to force a fresh pipeline run,
  or `rebuild_index_only.py` to only rebuild the RAG index (zero Gemini cost).
- Free-tier Gemini quota is ~20 requests/day per key — two keys are configured
  in `.streamlit/secrets.toml` (gitignored) and rotated automatically on 429.
- Large multi-document responses (many findings) are more likely to trip
  malformed-JSON or enum-mismatch issues than a single small document — worth
  testing with the biggest realistic doc set before a demo, not just one PDF.
- `st.chat_input` placed inside `st.sidebar` renders nothing (no error) in the
  installed Streamlit version — the chat assistant is deliberately in the main
  column, where `st.chat_input` pins to the bottom of the viewport.
- `_preview_dashboard.py` + `.claude/launch.json` are a DEV-ONLY harness that
  seeds Page 2 from the `.cache_multi/` analysis so the layout can be viewed
  without re-running upload/Gemini. Not part of the shipped app.
