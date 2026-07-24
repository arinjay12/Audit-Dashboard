# Handles all on-demand Gemini calls — persistent chat and click-to-explain on KPI cards and panels.

from core.gemini_client import generate
from core.schema import AuditAnalysis
from core import rag as rag_module


def _document_context(analysis: AuditAnalysis, document: str) -> str:
    """
    A summary scoped to ONE document: only the findings and discrepancies whose
    source is that document, plus the overall summary as light background. Used by
    the Page 3 (Detailed Insights) chat, which answers about a single file.
    """
    findings = [f for f in analysis.findings if f.source_doc == document]
    discrepancies = [d for d in analysis.discrepancies if d.source_doc == document]

    lines = [
        f"DOCUMENT IN FOCUS: {document}",
        f"\nOVERALL AUDIT BACKGROUND (context only, not the focus): {analysis.overall_summary}",
        f"\nFINDINGS FROM THIS DOCUMENT ({len(findings)}):",
    ]
    if findings:
        for f in findings:
            lines.append(f"  [{f.severity}] {f.title} — {f.category} — {f.status}")
            lines.append(f"    {f.description}")
            lines.append(f"    Recommendation: {f.recommendation}")
    else:
        lines.append("  (none attributed to this document)")

    lines.append(f"\nFINANCIAL DISCREPANCIES FROM THIS DOCUMENT ({len(discrepancies)}):")
    if discrepancies:
        for d in discrepancies:
            amount = f"${d.amount:,.2f}" if d.amount else "Amount not specified"
            lines.append(f"  {d.description} — {amount}")
    else:
        lines.append("  (none attributed to this document)")

    return "\n".join(lines)


def _analysis_as_context(analysis: AuditAnalysis, document: str = None) -> str:
    """
    Converts the AuditAnalysis object into a compact text summary to use as
    context in a Gemini call. By default it covers the whole audit; if `document`
    is given, it delegates to the single-document scoped summary instead.
    """
    if document:
        return _document_context(analysis, document)

    lines = []
    lines.append(f"AUDIT SUMMARY: {analysis.overall_summary}")
    lines.append(f"\nCOMPLIANCE SCORE: {analysis.compliance.score_pct}% ({analysis.compliance.framework})")
    lines.append(f"Items passed: {analysis.compliance.items_passed}, Items failed: {analysis.compliance.items_failed}")

    lines.append(f"\nKPIs:")
    lines.append(f"  Total findings: {analysis.kpis.total_findings}")
    lines.append(f"  High risk: {analysis.kpis.high_risk_count}, Medium: {analysis.kpis.medium_risk_count}, Low: {analysis.kpis.low_risk_count}")
    lines.append(f"  Pending action items: {analysis.kpis.pending_action_items}")
    lines.append(f"  Financial discrepancy flags: {analysis.kpis.financial_discrepancy_flags}")
    lines.append(f"  Overall vendor risk: {analysis.kpis.overall_vendor_risk}")

    lines.append(f"\nFINDINGS ({len(analysis.findings)} total):")
    for f in analysis.findings:
        lines.append(f"  [{f.severity}] {f.title} — {f.category} — {f.status} — Source: {f.source_doc}")
        lines.append(f"    {f.description}")
        lines.append(f"    Recommendation: {f.recommendation}")

    lines.append(f"\nRISKS ({len(analysis.risks)} total):")
    for r in analysis.risks:
        lines.append(f"  {r.title} — Likelihood: {r.likelihood}/5, Impact: {r.impact}/5")
        lines.append(f"    {r.description}")

    if analysis.vendors:
        lines.append(f"\nVENDORS:")
        for v in analysis.vendors:
            flags = ", ".join(v.flags) if v.flags else "None"
            lines.append(f"  {v.name} — Risk: {v.risk_rating} — Flags: {flags}")

    if analysis.discrepancies:
        lines.append(f"\nDISCREPANCIES:")
        for d in analysis.discrepancies:
            amount = f"${d.amount:,.2f}" if d.amount else "Amount not specified"
            lines.append(f"  {d.description} — {amount} — Source: {d.source_doc}")

    lines.append(f"\nRECOMMENDATIONS:")
    for i, rec in enumerate(analysis.recommendations, 1):
        lines.append(f"  {i}. {rec}")

    return "\n".join(lines)


def explain(topic: str, analysis: AuditAnalysis) -> str:
    """
    Called when a user clicks a KPI card or insight panel. Returns a detailed,
    grounded insight about that specific metric/panel — not a generic definition,
    but what THIS audit's numbers say and what to do about them.
    """
    context = _analysis_as_context(analysis)

    prompt = f"""
====== ROLE ======
You are a Senior Internal Auditor briefing an executive who just clicked on one
metric of an audit dashboard to understand it better. You are precise, grounded
strictly in the analysis below, and you never invent numbers or findings.

====== WHAT THE USER CLICKED ======
"{topic}"

====== STRUCTURED AUDIT SUMMARY (your only source of truth) ======
{context}

====== HOW TO RESPOND ======
Write a focused briefing on the clicked item — roughly 120-180 words — structured as:

1. **What it is** — state the actual number/value for this audit and what it counts.
2. **What's driving it** — name the specific findings, vendors, discrepancies, or
   compliance items behind the number (use their real titles/amounts from the
   summary above). This is the most important part; be concrete, not generic.
3. **Why it matters** — the business/risk implication for this organisation.
4. **What to do** — the most relevant next action, tied to the recommendations
   where possible.

Rules:
- Ground every claim in the summary above. Do NOT invent anything not present.
- Lead with the number, then the specifics behind it. Reference findings by name.
- Be an auditor talking to a decision-maker: direct, useful, no filler.
- Use short paragraphs or bullets. Do not restate this prompt or the raw summary.
"""
    return generate(prompt)


# How many characters of a document's raw text to send for summarisation. Keeps
# very large PDFs from ballooning the prompt while still covering the substance.
_DOC_TEXT_CAP = 40000


def summarize_document(document: str, analysis: AuditAnalysis, raw_text: str = None) -> str:
    """
    Generate a concise executive summary of ONE document, on demand (Page 3).
    Uses the document's raw extracted text when available (capped), anchored by
    its structured findings/discrepancies. Grounded strictly in that document.
    """
    scoped = _document_context(analysis, document)

    text_block = ""
    if raw_text:
        text_block = f"\n====== DOCUMENT TEXT (extracted) ======\n{raw_text[:_DOC_TEXT_CAP]}\n"

    prompt = f"""
====== ROLE ======
You are a Senior Internal Auditor. Summarise ONE audit document for an executive
reader — clear, specific, and grounded strictly in the material below. Never
speculate or pull in anything from other documents.

====== DOCUMENT ======
{document}
{text_block}
====== STRUCTURED FINDINGS FOR THIS DOCUMENT ======
{scoped}

====== WHAT TO WRITE ======
Write a concise summary of THIS document only (about 100-180 words):
- What the document is and its purpose / scope.
- Its most important findings, figures, dates, or issues (be specific — use real
  names and numbers from the material).
- The overall takeaway / risk picture for this document.
Use short paragraphs or a few bullets. Output only the summary — no preamble.
"""
    return generate(prompt)


def chat(user_message: str, analysis: AuditAnalysis, history: list,
         index=None, chunks=None, document: str = None) -> str:
    """
    Handles the persistent chat window. Every message is sent with:
    - The structured audit summary (findings, KPIs, vendors, etc.)
    - The most relevant raw document chunks retrieved via RAG
    - The last 10 messages of conversation history

    index and chunks come from rag.build_index() — stored in session state after upload.
    history is a list of dicts: [{"role": "user"|"assistant", "content": "..."}]

    If `document` is given (the Page 3 detailed view), the whole answer is scoped
    to that one file: the structured context is limited to it, RAG retrieval is
    restricted to its chunks, and the model is told to answer only about it.
    """
    context = _analysis_as_context(analysis, document=document)

    relevant_chunks = ""
    if index is not None and chunks:
        # Enrich the query with the user's own recent messages so follow-ups like
        # "what does it say" still retrieve the right chunks. We use only USER
        # turns (not the assistant's verbose replies, which would dilute the
        # query embedding and pull in off-topic chunks).
        rag_query = user_message
        if history:
            recent_user = [m["content"] for m in history[-6:] if m["role"] == "user"]
            if recent_user:
                rag_query = " ".join(recent_user[-2:] + [user_message])

        # Widen page detection (not the semantic query) with the assistant's last
        # reply — it may already cite "(p.7, ...)", so a follow-up like "when was
        # it signed?" still resolves to the right page even without repeating it.
        page_hint_text = user_message
        if history:
            last_assistant = next((m["content"] for m in reversed(history) if m["role"] == "assistant"), None)
            if last_assistant:
                page_hint_text = last_assistant + " " + user_message

        retrieved = rag_module.query(rag_query, index, chunks,
                                     page_hint_text=page_hint_text, source_filter=document)
        if retrieved:
            relevant_chunks = f"\nRELEVANT DOCUMENT EXCERPTS:\n{retrieved}\n"

    history_text = ""
    if history:
        history_text = "\nCONVERSATION SO FAR:\n"
        for msg in history[-10:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            history_text += f"{role}: {msg['content']}\n"

    scope_note = ""
    if document:
        scope_note = f"""
====== SCOPE: SINGLE DOCUMENT ======
This conversation is about ONE document only: "{document}".
The structured summary and the excerpts below are limited to that document.
- Answer only about "{document}". Do not bring in findings, figures, or facts from
  any other document.
- If the user asks which documents they can ask about, tell them this view is focused
  on "{document}".
- If the user asks about another document or the overall audit, say that this chat is
  scoped to "{document}" and that the main dashboard chat handles cross-document questions.
"""

    prompt = f"""
====== ROLE ======
You are a Senior Internal Auditor acting as an interactive assistant. The user has
uploaded a set of audit documents which have already been analysed, and they are now
asking you questions about them. You answer like an experienced audit professional:
precise, evidence-based, and grounded strictly in the material provided — never
speculative. You are talking to a client/colleague, so be clear and direct, not academic.
{scope_note}
====== WHAT YOU ARE WORKING WITH ======
You are given three things, in order of the prompt below:

1. STRUCTURED AUDIT SUMMARY — the high-level extracted picture of the whole audit
   (overall summary, KPIs, findings, risks, vendors, discrepancies, compliance,
   recommendations). Use this for big-picture questions ("how many high-risk
   findings?", "what's the overall compliance score?", "summarise the audit").

2. RELEVANT DOCUMENT EXCERPTS — verbatim passages retrieved from the original
   documents that best match the user's question. Each excerpt is tagged with its
   [Page N] and [Source: filename]. Use these for specific factual questions
   (exact wording, dates, names, amounts, "what does page N say?"). These are the
   ground truth for detail — prefer them over the summary when the two could differ.

3. CONVERSATION SO FAR — the recent back-and-forth, so you can resolve follow-up
   questions like "what about the second one?" or "and when was it dated?".

====== HOW TO ANSWER ======
- Decide what kind of question it is and draw from the right layer: summary for
  high-level, excerpts for specifics. It is fine to combine both.
- Ground every claim in the material above. Do NOT invent findings, vendors, dates,
  amounts, or conclusions that are not supported by the summary or the excerpts.
- Be exact with dates, numbers, names and figures. If several dates or amounts appear,
  distinguish them explicitly and never substitute one for another. Never guess a value
  that is not written down — if it is not there, say so.
- When the user asks "what does it say" or asks you to quote, reproduce the exact wording
  from the excerpts rather than paraphrasing loosely.
- When you state a specific fact, cite where it came from — the page number and/or the
  source filename (e.g. "(p.7, …annual-internal-audit-report.pdf)").
- If the answer genuinely is not in the summary or the excerpts, say so plainly and, if
  useful, tell the user what the documents DO cover on that topic. Do not fill the gap
  with assumptions.
- Some excerpts were recovered from scanned images via OCR and may contain minor
  spelling slips (e.g. "intemal" for "internal"); read them charitably but never add
  content that is not there.

====== MATCH THE DEPTH OF YOUR ANSWER TO THE QUESTION ======
Read what the user is actually asking for and size your response to it. Do NOT default
to a short 4-5 line reply for everything.

- Simple factual lookups ("how many high-risk findings?", "what's the compliance score?",
  "when was the letter signed?") → answer directly in a sentence or two. Don't pad.

- Requests to EXPLAIN, ELABORATE, or go into DETAIL — anything containing words like
  "explain", "in detail", "elaborate", "walk me through", "why", "how", "tell me more",
  "deep dive", "break down", "analyse", or "give me everything on X" → write a THOROUGH,
  well-developed response. This means several paragraphs (and/or a structured list),
  typically 200-500+ words. For these, do not just state the fact — fully develop it:
    • what it is and the exact specifics from the documents (names, figures, dates, pages),
    • the context and what is driving it (which findings/vendors/clauses, and why),
    • the implications and risk to the organisation,
    • what follows from it (remediation, recommendations, related findings).
  Keep going until the topic is genuinely covered — a detailed question deserves a
  complete answer, not a summary of one.

- "Summarise" / "overview" / "at a glance" → keep it tight and high-level, as asked.

Whatever the length, stay well-structured (lead with the direct answer, then develop it
with short paragraphs or bullets) and keep every claim grounded in the material above.
When in doubt about depth, err toward being more thorough and specific, not less.

====== STRUCTURED AUDIT SUMMARY ======
{context}
{relevant_chunks}{history_text}
====== USER'S LATEST MESSAGE ======
{user_message}

Answer now, following the rules above.
"""
    return generate(prompt)
