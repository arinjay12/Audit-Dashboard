# Plotly charts for the dashboard, each built from the validated AuditAnalysis.
# Every function returns a go.Figure so the page decides where to place it.

from collections import Counter

import plotly.graph_objects as go

from core.schema import AuditAnalysis
from ui.theme import SEVERITY_COLORS, STATUS_COLORS, SEVERITY_COLORS as SEV

# Shared layout applied to every figure. Uses plotly's magic-underscore keys so
# a per-chart `title_text=` can be passed alongside without colliding.
# Light text / transparent background so the charts sit on the dark app theme.
_LAYOUT = dict(
    margin=dict(l=10, r=10, t=40, b=10),
    height=300,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#E8E8EE", size=13),
    title_font_size=15,
)

_GRID = "#2F2F3A"   # subtle gridline colour on the dark charcoal theme


def severity_donut(findings) -> go.Figure:
    """Findings split by severity — the headline risk mix. Takes a list of
    findings so it works for the whole audit (Page 2) or one document (Page 3)."""
    order = ["High", "Medium", "Low"]
    counts = Counter(f.severity for f in findings)
    values = [counts.get(s, 0) for s in order]

    fig = go.Figure(go.Pie(
        labels=order,
        values=values,
        hole=0.58,
        marker=dict(colors=[SEVERITY_COLORS[s] for s in order]),
        textinfo="value",
        sort=False,
    ))
    total = sum(values)
    fig.update_layout(
        title_text="Findings by Severity",
        annotations=[dict(text=f"{total}<br>total", x=0.5, y=0.5,
                          font=dict(size=16), showarrow=False)],
        legend=dict(orientation="h", yanchor="bottom", y=-0.15),
        **_LAYOUT,
    )
    return fig


def status_bar(findings) -> go.Figure:
    """Remediation status of findings — how much work is still open."""
    order = ["Open", "In Progress", "Closed"]
    counts = Counter(f.status for f in findings)
    values = [counts.get(s, 0) for s in order]

    fig = go.Figure(go.Bar(
        x=values,
        y=order,
        orientation="h",
        marker=dict(color=[STATUS_COLORS[s] for s in order]),
        text=values,
        textposition="auto",
    ))
    fig.update_layout(title_text="Remediation Status", **_LAYOUT)
    fig.update_xaxes(showgrid=False, zeroline=False, visible=False)
    fig.update_yaxes(showgrid=False)
    return fig


def category_bar(findings) -> go.Figure:
    """Findings by category, stacked by severity so you see where the risk sits."""
    order = ["High", "Medium", "Low"]
    cats = list(dict.fromkeys(f.category for f in findings))  # preserve appearance order

    fig = go.Figure()
    for sev in order:
        counts = Counter(f.category for f in findings if f.severity == sev)
        fig.add_bar(
            name=sev,
            x=cats,
            y=[counts.get(c, 0) for c in cats],
            marker_color=SEVERITY_COLORS[sev],
        )
    fig.update_layout(
        title_text="Findings by Category",
        barmode="stack",
        legend=dict(orientation="h", yanchor="bottom", y=-0.25),
        **_LAYOUT,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor=_GRID)
    return fig


def risk_heatmap(analysis: AuditAnalysis) -> go.Figure:
    """
    5x5 likelihood × impact matrix. The background cells are shaded by their
    risk score (likelihood × impact) green→red, and each risk is plotted as a
    point at its (likelihood, impact) position. Overlapping risks are jittered
    slightly so they don't hide each other.
    """
    # Background: score = likelihood * impact, normalised to 0-1 for colour.
    z = [[(x * y) / 25 for x in range(1, 6)] for y in range(1, 6)]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=[1, 2, 3, 4, 5],
        y=[1, 2, 3, 4, 5],
        colorscale=[[0, "#e6f0e6"], [0.5, "#f5e6c8"], [1, "#f0cccc"]],
        showscale=False,
        hoverinfo="skip",
    ))

    # Overlay the actual risks. Jitter duplicates on the same cell.
    seen = {}
    xs, ys, texts = [], [], []
    for r in analysis.risks:
        key = (r.likelihood, r.impact)
        n = seen.get(key, 0)
        seen[key] = n + 1
        offset = 0.12 * n
        xs.append(min(5, r.likelihood + offset))
        ys.append(min(5, r.impact + offset))
        texts.append(f"{r.title}<br>L{r.likelihood} × I{r.impact}")

    if xs:
        fig.add_scatter(
            x=xs, y=ys, mode="markers",
            marker=dict(size=14, color="#2f3e4e",
                        line=dict(color="white", width=1.5)),
            text=texts, hoverinfo="text",
        )

    fig.update_layout(title_text="Risk Matrix (Likelihood × Impact)", **_LAYOUT)
    fig.update_xaxes(title="Likelihood", tickmode="array", tickvals=[1, 2, 3, 4, 5],
                     showgrid=False, range=[0.5, 5.5])
    fig.update_yaxes(title="Impact", tickmode="array", tickvals=[1, 2, 3, 4, 5],
                     showgrid=False, range=[0.5, 5.5])
    return fig


def compliance_gauge(analysis: AuditAnalysis) -> go.Figure:
    """A gauge for the overall compliance percentage."""
    score = analysis.compliance.score_pct
    colour = SEV["Low"] if score >= 75 else SEV["Medium"] if score >= 50 else SEV["High"]

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number=dict(suffix="%"),
        gauge=dict(
            axis=dict(range=[0, 100]),
            bar=dict(color=colour),
            steps=[
                dict(range=[0, 50], color="#f7e3e3"),
                dict(range=[50, 75], color="#faf0da"),
                dict(range=[75, 100], color="#e6f0e6"),
            ],
        ),
    ))
    fig.update_layout(title_text="Compliance Score", **_LAYOUT)
    return fig
