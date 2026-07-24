# The text/list panels below the charts: findings, vendors, discrepancies,
# recommendations. Each renders directly from the validated AuditAnalysis.

import streamlit as st

from core.schema import AuditAnalysis
from ui.theme import severity_color, status_color, RISK_COLORS, MUTED, section_header
from ui.insight_dialog import open_insight


def _panel_header(icon: str, title: str, accent: str, topic: str, note: str = ""):
    """A colour-coded section heading with a 'Discuss with AI' button on the right."""
    left, right = st.columns([3, 1])
    with left:
        section_header(icon, title, accent, note=note)
    if right.button("💬 Discuss", key=f"panel_{topic}", use_container_width=True):
        open_insight(topic)


def _badge(text: str, color: str) -> str:
    """Small coloured pill for severity/status/risk labels."""
    return (
        f"<span style='background:{color};color:white;padding:2px 9px;"
        f"border-radius:11px;font-size:0.72rem;font-weight:600;"
        f"white-space:nowrap'>{text}</span>"
    )


def render_finding_list(findings):
    """
    Render a given list of findings, sorted High → Low, each expandable to its
    detail + recommendation. Shared by the dashboard (all findings) and the
    detailed-insights page (findings filtered to one document).
    """
    order = {"High": 0, "Medium": 1, "Low": 2}
    # Coloured dot in the collapsed label so severity is visible BEFORE expanding
    # (expander labels support Streamlit's markdown colour directives).
    dots = {"High": ":red[●]", "Medium": ":orange[●]", "Low": ":green[●]"}
    for f in sorted(findings, key=lambda f: order.get(f.severity, 3)):
        header = (
            f"{_badge(f.severity, severity_color(f.severity))} &nbsp; "
            f"{_badge(f.status, status_color(f.status))} &nbsp; "
            f"**{f.title}**"
        )
        label = f"{dots.get(f.severity, '')} {f.title} — {f.severity}"
        with st.expander(label, expanded=False):
            st.markdown(header, unsafe_allow_html=True)
            st.markdown(f"**Category:** {f.category} &nbsp;|&nbsp; "
                        f"**Source:** `{f.source_doc}`")
            st.markdown(f.description)
            st.markdown(f"**Recommendation:** {f.recommendation}")


def render_findings(analysis: AuditAnalysis):
    """Findings breakdown panel for the dashboard — all findings, filterable."""
    _panel_header("📋", "Findings Breakdown", "#FF6B81", "Findings Breakdown",
                  note=f"{len(analysis.findings)} total")
    if not analysis.findings:
        st.info("No findings were extracted from these documents.")
        return

    # Quick filters. Empty selection = show everything.
    sev = st.pills("Severity", ["High", "Medium", "Low"],
                   selection_mode="multi", key="findings_sev_filter",
                   label_visibility="collapsed")
    findings = [f for f in analysis.findings if not sev or f.severity in sev]

    if findings:
        st.caption(f"Showing {len(findings)} of {len(analysis.findings)} findings")
        render_finding_list(findings)
    else:
        st.info("No findings match the selected filters.")


def render_vendors(analysis: AuditAnalysis):
    """Vendor list with risk badge and any flags."""
    _panel_header("🏢", "Vendors", "#977CFF", "Vendor Risk Summary")
    if not analysis.vendors:
        st.info("No vendors were identified.")
        return

    order = {"High": 0, "Medium": 1, "Low": 2}
    vendors = sorted(analysis.vendors, key=lambda v: order.get(v.risk_rating, 3))

    for v in vendors:
        badge = _badge(v.risk_rating, RISK_COLORS.get(v.risk_rating, MUTED))
        flags = (" · ".join(v.flags)) if v.flags else "No flags"
        st.markdown(
            f"{badge} &nbsp; **{v.name}**<br>"
            f"<span style='color:{MUTED};font-size:0.85rem'>{flags}</span>",
            unsafe_allow_html=True,
        )
        st.write("")


def render_discrepancies(analysis: AuditAnalysis):
    """Financial discrepancies with amounts and source docs."""
    _panel_header("💸", "Financial Discrepancies", "#FFB020", "Financial Discrepancies")
    if not analysis.discrepancies:
        st.info("No financial discrepancies were flagged.")
        return

    total = 0.0
    for d in analysis.discrepancies:
        amount = f"${d.amount:,.2f}" if d.amount is not None else "—"
        if d.amount is not None:
            total += d.amount
        st.markdown(
            f"**{amount}** &nbsp; {d.description}<br>"
            f"<span style='color:{MUTED};font-size:0.8rem'>Source: {d.source_doc}</span>",
            unsafe_allow_html=True,
        )
        st.write("")

    if total:
        st.markdown(f"**Total flagged: ${total:,.2f}**")


def render_recommendations(analysis: AuditAnalysis):
    """Prioritised recommendation list."""
    _panel_header("✅", "Priority Recommendations", "#2DD4BF", "Priority Recommendations")
    if not analysis.recommendations:
        st.info("No recommendations were generated.")
        return
    for i, rec in enumerate(analysis.recommendations, 1):
        st.markdown(f"**{i}.** {rec}")
        st.write("")
