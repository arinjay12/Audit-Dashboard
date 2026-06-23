# Handles all on-demand Gemini calls — persistent chat and click-to-explain on KPI cards and panels.

import json
from core.gemini_client import generate
from core.schema import AuditAnalysis


def _analysis_as_context(analysis: AuditAnalysis) -> str:
    """
    Converts the AuditAnalysis object into a compact text summary to use as
    context in every Gemini call. This means Gemini always knows the full
    picture of the audit when answering questions.
    """
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
    Called when a user clicks a KPI card or insight panel.
    Returns a plain-English explanation of that specific metric in the context
    of the uploaded audit documents.
    """
    context = _analysis_as_context(analysis)

    prompt = f"""You are an expert auditor explaining audit findings to a client.
Below is a structured summary of the audit analysis:

{context}

The user clicked on: "{topic}"

Explain this specific metric clearly and concisely in 3-5 sentences.
Focus on what it means, why it matters, and what the numbers indicate for this specific audit.
Do not repeat generic definitions — speak directly to the numbers and context above.
"""
    return generate(prompt)


def chat(user_message: str, analysis: AuditAnalysis, history: list) -> str:
    """
    Handles the persistent chat window. Every message is sent with:
    - The full audit analysis as context
    - The conversation history so Gemini remembers what was said

    history is a list of dicts: [{"role": "user"|"assistant", "content": "..."}]
    """
    context = _analysis_as_context(analysis)

    # Build the conversation history as a readable string
    history_text = ""
    if history:
        history_text = "\nCONVERSATION SO FAR:\n"
        for msg in history[-10:]:  # only last 10 messages to keep prompt size reasonable
            role = "User" if msg["role"] == "user" else "Assistant"
            history_text += f"{role}: {msg['content']}\n"

    prompt = f"""You are an expert auditor assistant helping a user analyse their audit documents.
Below is the full audit analysis extracted from their uploaded documents:

{context}
{history_text}
User's latest message: {user_message}

Answer helpfully and concisely based on the audit data above.
If the user asks about something not covered in the audit data, say so clearly.
"""
    return generate(prompt)
