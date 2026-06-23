"""
Sends all extracted document text to Gemini in one call and returns
a validated AuditAnalysis object.

Entry point: analyze(docs) -> AuditAnalysis
"""

from core.schema import ParsedDoc, AuditAnalysis
from core.gemini_client import generate_json


# ── prompt builder ────────────────────────────────────────────────────────────

def _build_prompt(docs: list[ParsedDoc]) -> str:
    """
    Combines all parsed document text into one prompt string.
    The instructions are hardcoded; only the document content changes each run.
    """

    # Step 1: paste in all the document text with labels
    doc_sections = []
    for i, doc in enumerate(docs, start=1):
        section = f"--- Document {i}: {doc.filename} ---\n{doc.raw_text}"
        doc_sections.append(section)

    all_documents = "\n\n".join(doc_sections)

    # Step 2: the hardcoded instruction telling Gemini what to extract
    prompt = f"""
You are a senior auditor reviewing a set of audit documents.
Read all the documents below carefully and extract the information specified.

====== DOCUMENTS ======

{all_documents}

====== INSTRUCTIONS ======

Extract the following from the documents above and return as valid JSON.
Follow the structure exactly — field names, types, and allowed values must match.

{{
  "overall_summary": "2-3 sentence summary of the overall audit findings",

  "findings": [
    {{
      "title": "short name of the finding",
      "description": "what the issue is",
      "severity": "High | Medium | Low",
      "category": "Financial | Compliance | Operational | IT | HR | Other",
      "source_doc": "which filename this came from",
      "status": "Open | In Progress | Closed",
      "recommendation": "what should be done to fix it"
    }}
  ],

  "risks": [
    {{
      "title": "name of the risk",
      "description": "description of the risk",
      "likelihood": 1,
      "impact": 1,
      "category": "Financial | Operational | Compliance | Reputational | Other"
    }}
  ],

  "vendors": [
    {{
      "name": "vendor name",
      "risk_rating": "High | Medium | Low",
      "flags": ["list", "of", "specific", "concerns"]
    }}
  ],

  "discrepancies": [
    {{
      "description": "what the discrepancy is",
      "amount": 0.0,
      "source_doc": "which filename this came from"
    }}
  ],

  "compliance": {{
    "score_pct": 0.0,
    "framework": "name of the compliance framework e.g. ISO 27001 or Internal Policy",
    "items_passed": 0,
    "items_failed": 0,
    "details": ["list of key pass/fail notes"]
  }},

  "kpis": {{
    "total_findings": 0,
    "high_risk_count": 0,
    "medium_risk_count": 0,
    "low_risk_count": 0,
    "pending_action_items": 0,
    "financial_discrepancy_flags": 0,
    "overall_vendor_risk": "High | Medium | Low"
  }},

  "recommendations": [
    "top-level recommendation 1",
    "top-level recommendation 2"
  ]
}}

Rules:
- severity, status, risk_rating, overall_vendor_risk must use exactly the values shown above
- likelihood and impact must be integers between 1 and 5
- score_pct must be a number between 0 and 100
- amount in discrepancies can be null if no specific amount is mentioned
- if a field has no data (e.g. no vendors mentioned), return an empty list
- return JSON only, no explanation or markdown
"""

    return prompt



def analyze(docs: list[ParsedDoc]) -> AuditAnalysis:
    """
    Takes parsed documents, calls Gemini once, returns a validated AuditAnalysis.
    Raises ValueError if Gemini's response doesn't match the schema.
    """
    prompt = _build_prompt(docs)

    raw = generate_json(prompt)

    try:
        analysis = AuditAnalysis(**raw)
    except Exception as e:
        raise ValueError(f"Gemini response did not match the AuditAnalysis schema.\nError: {e}") from e

    return analysis
