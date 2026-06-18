"""
Conversational layer: the persistent chat + click-to-explain insights.

These are the ONLY on-demand LLM calls in the running app. Each call is fed:
  - the structured AuditAnalysis object (compact, authoritative context)
  - relevant raw document text (retrieved per question)
  - the running chat history

Used by both Page 2 (whole-document-set chat / KPI & panel explanations) and
Page 3 (same, scoped to a specific document when asked).

TODO(week 4): context assembly, click-to-explain prompts, chart-on-request.
"""
