"""
Analysis: parsed document text -> validated AuditAnalysis object.

The heart of the schema-first design. One Gemini call (or a map-reduce over
documents for very large sets) populates the AuditAnalysis schema via
structured JSON output. Result is cached so the dashboard never re-calls the
LLM just to re-render.

TODO(week 2): prompt design, structured-output call, map-reduce for big ZIPs,
validation + graceful fallback when a field can't be inferred.
"""
