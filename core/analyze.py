"""
Sends all extracted document text to Gemini in one call and returns
a validated AuditAnalysis object.

Entry point: analyze(docs) -> AuditAnalysis
"""

from core.schema import ParsedDoc, AuditAnalysis
from core.gemini_client import generate_json


# ── prompt builder ────────────────────────────────────────────────────────────

# Per-document character cap for the analysis prompt. Generous (~30k tokens per
# document) — real audit reports fit comfortably — but stops one enormous file
# from blowing past the model's context window and degrading the whole analysis.
_DOC_CHAR_CAP = 120_000


def _build_prompt(docs: list[ParsedDoc]) -> str:
    """
    Combines all parsed document text into one prompt string.
    The instructions are hardcoded; only the document content changes each run.
    """

    # Step 1: paste in all the document text with labels
    doc_sections = []
    for i, doc in enumerate(docs, start=1):
        text = doc.raw_text
        if len(text) > _DOC_CHAR_CAP:
            text = (text[:_DOC_CHAR_CAP]
                    + "\n[NOTE: this document was truncated for length — the text above "
                      "is its first portion.]")
        section = f"--- Document {i}: {doc.filename} ---\n{text}"
        doc_sections.append(section)

    all_documents = "\n\n".join(doc_sections)

    # Step 2: the hardcoded instruction telling Gemini what to extract.
    # This is a deliberately detailed prompt: a clear role, explicit rating
    # rubrics, internal-consistency rules, and anti-hallucination guardrails.
    # The rubrics make every rating reproducible and defensible — you can
    # explain *why* something is High vs Medium, not just that the model said so.
    prompt = f"""
====== ROLE ======
You are a Senior Internal Auditor with years of experience across financial,
operational, IT, compliance and vendor/third-party audits. You write findings in a way that
is : precise, evidence-based, and tied directly to
the source documents. You never speculate beyond what the evidence supports.

====== OBJECTIVE ======
Analyse the audit documents provided below and produce a single structured JSON
object capturing the complete audit picture: findings, risks, vendors, financial
discrepancies, compliance status, headline KPIs, and prioritised recommendations.
This JSON drives an executive dashboard, so it must be accurate, complete, and
internally consistent.

====== HOW TO READ THE DOCUMENTS ======
- Documents are separated by "--- Document N: filename ---" headers. Use the exact
  filename when populating any "source_doc" field.
- Within a document, pages are marked "[Page N]". When you cite a specific fact,
  attribute it to the correct page/source.
- Tables are rendered between "[TABLE ...]" and "[END TABLE]" markers with explicit
  "Columns:" and "Row N:" lines. Read these as structured data, not prose.
- Some text was recovered from scanned images via OCR and may contain minor spelling
  errors (e.g. "intemal" for "internal"). Interpret obvious OCR typos charitably, but
  never invent content that isn't there.

====== EXTRACTION GUIDE (field by field) ======

FINDINGS — every distinct issue, control weakness, exception, or deficiency the
auditors identified. Extract ALL of them; do not merge separate issues or stop early.
  • title: a short, specific label (e.g. "Segregation of Duties Violation in AP").
  • description: what the issue is, with concrete detail from the document (amounts,
    counts, dates, systems involved). 1–3 sentences.
  • severity: rate using the SEVERITY RUBRIC below.
  • category: one of Financial | Compliance | Operational | IT | HR | Other.
  • source_doc: the exact filename the finding came from.
  • status: one of Open | In Progress | Closed, using the STATUS RUBRIC below.
  • recommendation: the specific corrective action. If the document states management's
    action plan, use it; otherwise propose a concrete, professional remediation.

RISKS — forward-looking exposures (what could go wrong), distinct from findings
(what already did). Extract risks named in the documents and material risks clearly
implied by the findings.
  • likelihood: integer 1–5 (LIKELIHOOD RUBRIC below).
  • impact: integer 1–5 (IMPACT RUBRIC below).
  • category: Financial | Operational | Compliance | Reputational | Other.

VENDORS — third parties / suppliers / service providers named in the documents.
  • risk_rating: High | Medium | Low (VENDOR RISK RUBRIC below). If not explicitly
    stated, infer it from contract value, criticality of service, and any flags.
  • flags: list of specific concerns (e.g. "no signed contract", "SOC 2 expired",
    "overbilling"). Empty list if none.

DISCREPANCIES — financial mismatches, unexplained variances, overbillings, or
amounts that don't reconcile.
  • amount: the dollar figure involved as a number (no symbols/commas). Use null only
    if no specific amount is stated.
  • source_doc: the exact filename.

COMPLIANCE — overall conformance to the relevant framework/standard.
  • framework: the standard referenced (e.g. "ISO 27001", "SOX", "GAGAS", "IIA
    Standards", "Internal Policy"). If several apply, name the primary one(s).
  • items_passed / items_failed: counts of compliant vs non-compliant items if the
    documents enumerate them; otherwise your best evidence-based estimate.
  • score_pct: items_passed / (items_passed + items_failed) × 100, rounded to one
    decimal — unless the documents state an explicit compliance percentage, in which
    case use that.
  • details: short bullet notes on the key pass/fail items.

RECOMMENDATIONS — 3 to 6 prioritised, executive-level actions that address the most
material findings and risks first. Make them specific and actionable, not generic.

====== RATING RUBRICS ======

SEVERITY (findings):
  • High   — material financial impact, legal/regulatory non-compliance, data/security
             exposure, fraud risk, or a threat to operational continuity. Needs urgent action.
  • Medium — a real control weakness or process gap that should be remediated but is not
             immediately critical.
  • Low    — minor, low-impact, or housekeeping issue.
  Rate DECISIVELY against these definitions — do not default to Medium when unsure.
  Unencrypted data, unrevoked access, missing critical controls, regulatory breaches
  and material overbilling are High. Housekeeping and minor documentation gaps are Low.
  A typical audit produces findings at all three levels.

STATUS (findings):
  • Open        — identified; no remediation started.
  • In Progress — remediation underway or partially implemented.
  • Closed      — resolved / fully implemented / verified.
  A source document may use its own wording for status (e.g. "Partially
  Implemented", "Remediated", "Not Started"). Always map it to the closest of
  these three exact values — never copy the source's own phrasing verbatim.

LIKELIHOOD (risks, 1–5): 1 Rare · 2 Unlikely · 3 Possible · 4 Likely · 5 Almost certain.
IMPACT     (risks, 1–5): 1 Insignificant · 2 Minor · 3 Moderate · 4 Major · 5 Severe/critical.

VENDOR RISK:
  • High   — large/critical contract, or control failures, compliance flags, or active disputes.
  • Medium — moderate exposure or minor flags.
  • Low    — small, non-critical engagement with no flags.

====== KPI DERIVATION (must tie out exactly) ======
Compute the kpis block FROM the arrays above so the numbers are internally consistent:
  • total_findings            = the number of items in "findings".
  • high_risk_count           = findings whose severity == "High".
  • medium_risk_count         = findings whose severity == "Medium".
  • low_risk_count            = findings whose severity == "Low".
    (high + medium + low MUST equal total_findings.)
  • pending_action_items      = findings whose status is "Open" or "In Progress".
  • financial_discrepancy_flags = the number of items in "discrepancies".
  • overall_vendor_risk       = the highest risk_rating among vendors
                                (High if any High; else Medium if any Medium; else Low).

====== ACCURACY & ANTI-HALLUCINATION RULES ======
- Ground every field in the documents. Do NOT invent vendors, amounts, dates, or
  findings that aren't supported by the text.
- Be exhaustive but do not duplicate: each distinct issue appears once.
- Prefer concrete specifics (figures, counts, dates, system/process names) over vague
  language wherever the documents provide them.
- severity, status, risk_rating and overall_vendor_risk must use EXACTLY the allowed
  values and must never be null.
- likelihood and impact are integers 1–5. score_pct is a number 0–100.
- If a whole category has no data (e.g. no vendors are mentioned), return an empty list
  for it — do not fabricate placeholder entries.
- If the documents contain little or no genuine audit-related content, return empty
  lists and an overall_summary saying exactly that — NEVER invent findings, vendors,
  or figures to fill the structure.
- Work through the documents carefully and reason internally, but output ONLY the final
  JSON object — no commentary, no markdown, no code fences.

====== DOCUMENTS ======

{all_documents}

====== OUTPUT FORMAT ======
Return a single JSON object with EXACTLY this structure (field names, nesting and
allowed values must match):

{{
  "overall_summary": "2-3 sentence executive summary of the overall audit outcome",

  "findings": [
    {{
      "title": "short name of the finding",
      "description": "what the issue is, with concrete detail",
      "severity": "High | Medium | Low",
      "category": "Financial | Compliance | Operational | IT | HR | Other",
      "source_doc": "exact filename this came from",
      "status": "Open | In Progress | Closed",
      "recommendation": "specific corrective action"
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
      "flags": ["specific", "concerns"]
    }}
  ],

  "discrepancies": [
    {{
      "description": "what the discrepancy is",
      "amount": 0.0,
      "source_doc": "exact filename this came from"
    }}
  ],

  "compliance": {{
    "score_pct": 0.0,
    "framework": "primary compliance framework",
    "items_passed": 0,
    "items_failed": 0,
    "details": ["key pass/fail notes"]
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
    "prioritised recommendation 1",
    "prioritised recommendation 2"
  ]
}}
"""

    return prompt



def analyze(docs: list[ParsedDoc]) -> AuditAnalysis:
    """
    Takes parsed documents, calls Gemini once, returns a validated AuditAnalysis.
    Raises ValueError if Gemini's response doesn't match the schema, or if no
    document produced any readable text (analysing nothing invites fabrication).
    """
    if not any(d.raw_text.strip() for d in docs):
        raise ValueError(
            "No readable content was found in the uploaded documents. Check that the "
            "ZIP contains supported, non-empty files (PDF, DOCX, XLSX, CSV, TXT)."
        )

    prompt = _build_prompt(docs)

    raw = generate_json(prompt)

    try:
        analysis = AuditAnalysis(**raw)
    except Exception as e:
        raise ValueError(f"Gemini response did not match the AuditAnalysis schema.\nError: {e}") from e

    return analysis
