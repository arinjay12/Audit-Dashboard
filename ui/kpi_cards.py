# The top row of KPI cards on the dashboard. Reads straight from the validated
# KPIs block so the numbers always tie out with the findings/discrepancy lists.

import streamlit as st

from core.schema import AuditAnalysis
from ui.theme import SEVERITY_COLORS, NEUTRAL, MUTED, INK, RISK_COLORS, CARD_BG, CARD_BORDER
from ui.insight_dialog import open_insight


def _card(col, label: str, value, accent: str, sub: str = "", topic: str = None):
    """
    Render one coloured metric card into the given column, with a click-to-explain
    button beneath it. `topic` is the string passed to the AI insight modal.
    """
    sub_html = f"<div style='color:{MUTED};font-size:0.72rem;margin-top:2px'>{sub}</div>" if sub else ""
    col.markdown(
        f"""
        <div class="kpi-card" style="
            background:
                linear-gradient(150deg, {accent}24 0%, rgba(0,0,0,0) 46%),
                linear-gradient(180deg, #24242F 0%, #1C1C25 100%);
            border:1px solid {CARD_BORDER};
            border-left:5px solid {accent};
            border-radius:8px 8px 0 0;
            padding:14px 16px 10px;
            box-shadow:0 6px 20px {accent}14, 0 1px 3px rgba(0,0,0,0.25);
            height:120px;
            box-sizing:border-box;
            display:flex;
            flex-direction:column;
            overflow:hidden;
        ">
            <div style="color:{MUTED};font-size:0.78rem;font-weight:600;
                        text-transform:uppercase;letter-spacing:0.03em;
                        min-height:2.1em;display:flex;align-items:flex-start">{label}</div>
            <div style="color:{INK};font-size:1.9rem;font-weight:700;line-height:1.15;
                        margin-top:2px">{value}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
    if topic and col.button("🔍 AI Insight", key=f"kpi_{topic}", use_container_width=True):
        open_insight(topic)


def render_mini_kpis(items):
    """
    A compact, non-clickable KPI strip — small rectangles roughly the height of
    a stepper chip. Every cell gets flex:1 so the strip spans the full page
    width with even spacing. Used on Page 3 for the selected document's numbers.
    `items` is a list of (label, value, accent_color) tuples.
    """
    cells = []
    for label, value, accent in items:
        cells.append(
            f"<div style='flex:1 1 0;background:"
            f"linear-gradient(150deg, {accent}1c 0%, rgba(0,0,0,0) 50%), {CARD_BG};"
            f"border:1px solid {CARD_BORDER};"
            f"border-left:4px solid {accent};border-radius:6px;"
            f"padding:7px 10px;display:flex;align-items:baseline;"
            f"justify-content:center;gap:8px;min-width:0'>"
            f"<span style='color:{INK};font-size:1.05rem;font-weight:700'>{value}</span>"
            f"<span style='color:{MUTED};font-size:.7rem;font-weight:600;"
            f"text-transform:uppercase;letter-spacing:.03em;white-space:nowrap'>{label}</span>"
            f"</div>"
        )
    st.markdown(
        "<div style='display:flex;gap:10px;margin:6px 0 2px 0;width:100%'>"
        + "".join(cells) + "</div>",
        unsafe_allow_html=True,
    )


def render_kpi_cards(analysis: AuditAnalysis):
    """Two rows of KPI cards summarising the whole audit at a glance."""
    k = analysis.kpis

    # Row 1 — volume and urgency.
    c1, c2, c3, c4 = st.columns(4)
    _card(c1, "Total Findings", k.total_findings, NEUTRAL,
          topic="Total Audit Findings")
    _card(c2, "High Risk", k.high_risk_count, SEVERITY_COLORS["High"],
          sub=f"{k.medium_risk_count} medium · {k.low_risk_count} low",
          topic="High Risk Findings")
    _card(c3, "Pending Actions", k.pending_action_items, SEVERITY_COLORS["Medium"],
          sub="open or in progress", topic="Pending Action Items")
    _card(c4, "Discrepancy Flags", k.financial_discrepancy_flags, SEVERITY_COLORS["High"],
          sub="financial mismatches", topic="Financial Discrepancy Flags")

    st.write("")  # small vertical gap

    # Row 2 — compliance and vendor exposure.
    c5, c6, c7, c8 = st.columns(4)
    _card(c5, "Compliance Score", f"{analysis.compliance.score_pct:.0f}%", NEUTRAL,
          sub=analysis.compliance.framework[:28], topic="Compliance Score")
    _card(c6, "Items Passed", analysis.compliance.items_passed, SEVERITY_COLORS["Low"],
          topic="Compliance Items Passed")
    _card(c7, "Items Failed", analysis.compliance.items_failed, SEVERITY_COLORS["High"],
          topic="Compliance Items Failed")
    _card(c8, "Overall Vendor Risk", k.overall_vendor_risk,
          RISK_COLORS.get(k.overall_vendor_risk, MUTED),
          sub=f"{len(analysis.vendors)} vendors reviewed",
          topic="Overall Vendor Risk")
