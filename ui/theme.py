# Shared colours and styling helpers so cards, charts, and badges stay visually
# consistent across the dashboard. One place to change the palette.
#
# Palette: EY-inspired — charcoal surfaces with the signature yellow (#FFE600)
# used sparingly as an accent (thin borders, chips, highlights), not as large
# colour blocks. Severity keeps its own red/amber/green scale everywhere.

import streamlit as st

# Severity / status / vendor-risk colours. Same three-tone scale everywhere:
# red = worst, amber = middle, green = best. Tuned to read on a dark surface.
SEVERITY_COLORS = {
    "High":   "#e05561",   # red
    "Medium": "#e0a458",   # amber
    "Low":    "#4cae7d",   # green
}

STATUS_COLORS = {
    "Open":        "#e05561",   # red — nothing done yet
    "In Progress": "#e0a458",   # amber — underway
    "Closed":      "#4cae7d",   # green — resolved
}

RISK_COLORS = SEVERITY_COLORS   # vendor risk_rating uses the same High/Medium/Low scale

# Surfaces and text for the dark charcoal theme.
ACCENT = "#FFE600"       # EY yellow — accents, highlights, primary actions
CARD_BG = "#23232C"      # card / panel surface (matches secondaryBackgroundColor)
CARD_BORDER = "#34343F"  # subtle card border
NEUTRAL = ACCENT         # informational KPI accents use the brand yellow
INK = "#F2F2F5"          # primary light text on dark surfaces
MUTED = "#9A9AA6"        # secondary / label text


def severity_color(level: str) -> str:
    return SEVERITY_COLORS.get(level, MUTED)


def status_color(level: str) -> str:
    return STATUS_COLORS.get(level, MUTED)


def inject_css():
    """
    Global CSS applied on every page: Inter font, accent-underlined section
    headers, KPI card hover lift, hero/chip/stepper styles, and a contrast fix
    so primary (yellow) buttons get dark text. Pure CSS — no JS, no components.
    """
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

        html, body { font-family: 'Inter', 'Segoe UI', sans-serif; }
        h1, h2, h3, h4, h5, h6, p, label, button, input, textarea, select {
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }
        code, pre, kbd, samp { font-family: 'Source Code Pro', Consolas, monospace; }

        /* Section headers get a short accent underline */
        h2, h3 { position: relative; padding-bottom: 8px; letter-spacing: -0.01em; }
        h2::after, h3::after {
            content: ""; position: absolute; left: 0; bottom: 0;
            width: 34px; height: 3px; border-radius: 2px;
            background: #FFE600; opacity: .85;
        }

        /* KPI cards lift slightly on hover with a faint yellow edge */
        .kpi-card { transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease; }
        .kpi-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 22px rgba(0,0,0,.5);
            border-color: rgba(255,230,0,.55) !important;
        }

        /* Primary buttons: yellow→amber gradient, dark text, glow on hover */
        button[data-testid="stBaseButton-primary"], button[kind="primary"] {
            color: #17171E !important; font-weight: 700;
            background: linear-gradient(135deg, #FFE600 0%, #FFC300 100%) !important;
            border: none !important;
            transition: box-shadow .2s ease, transform .15s ease;
        }
        button[data-testid="stBaseButton-primary"]:hover:enabled {
            box-shadow: 0 4px 20px rgba(255,230,0,.35);
            transform: translateY(-1px);
        }

        /* Section band — a strong breaker that makes a section stand out */
        .section-band {
            display: flex; align-items: center; gap: 10px;
            background: linear-gradient(90deg, rgba(255,230,0,.12), rgba(255,230,0,.02) 70%, transparent);
            border-left: 4px solid #FFE600;
            border-radius: 8px;
            padding: 12px 18px;
            margin: 4px 0 14px 0;
            font-size: 1.06rem; font-weight: 700; color: #F2F2F5;
        }

        /* Expanders: rounded card look with an accent hover */
        [data-testid="stExpander"] details {
            border: 1px solid #34343F; border-radius: 10px; background: #1C1C24;
            transition: border-color .2s ease;
        }
        [data-testid="stExpander"] details:hover { border-color: rgba(255,230,0,.35); }

        /* Sidebar: subtle vertical gradient + a defining right edge */
        [data-testid="stSidebar"] {
            border-right: 1px solid #2A2A34;
            background: linear-gradient(180deg, #1C1C24 0%, #17171E 100%);
        }

        /* Active page in the top nav gets a yellow underline */
        a[aria-current="page"] {
            border-bottom: 2px solid #FFE600 !important;
            background: rgba(255,230,0,.06);
            border-radius: 6px 6px 0 0;
        }
        a[aria-current="page"] span { color: #F2F2F5 !important; }

        /* File-upload dropzone: dashed border that glows on hover */
        [data-testid="stFileUploaderDropzone"] {
            border: 1.5px dashed #3E3E4A; border-radius: 10px;
            transition: border-color .2s ease, background .2s ease;
        }
        [data-testid="stFileUploaderDropzone"]:hover {
            border-color: rgba(255,230,0,.65);
            background: rgba(255,230,0,.04);
        }

        /* Layered background: yellow + violet + blue ambient glows over a faint
           blueprint grid on a deep charcoal base — depth instead of a flat slab */
        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(700px 340px at 10% -4%, rgba(255,230,0,.07), transparent 60%),
                radial-gradient(900px 460px at 92% 0%, rgba(124,92,255,.055), transparent 60%),
                radial-gradient(900px 520px at 50% 112%, rgba(56,132,255,.05), transparent 60%),
                linear-gradient(rgba(255,255,255,.016) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,.016) 1px, transparent 1px),
                #14141B;
            background-size: auto, auto, auto, 44px 44px, 44px 44px, auto;
        }

        /* Entrance animation — content fades up as a page renders */
        @keyframes fadeUp {
            from { opacity: 0; transform: translateY(14px); }
            to   { opacity: 1; transform: none; }
        }
        h1 { animation: fadeUp .4s ease both; }

        /* Hero (upload page) */
        .hero-title {
            font-size: 2.5rem; font-weight: 800; line-height: 1.15;
            letter-spacing: -0.02em; animation: fadeUp .5s ease both;
        }
        .hero-title .accent {
            background: linear-gradient(90deg, #FFE600 0%, #FFC300 100%);
            -webkit-background-clip: text; background-clip: text; color: transparent;
        }
        .hero-sub {
            color: #9A9AA6; font-size: 1.03rem; margin-top: 10px; max-width: 640px;
            animation: fadeUp .5s ease .08s both;
        }

        /* Small stat chips — staggered entrance, brighten on hover */
        .chip {
            display: inline-block; padding: 6px 14px; margin: 0 8px 8px 0;
            border-radius: 16px; font-size: .8rem; font-weight: 600; color: #F2F2F5;
            background: rgba(255,230,0,.07); border: 1px solid rgba(255,230,0,.35);
            animation: fadeUp .45s ease both;
            transition: background .2s ease, border-color .2s ease;
        }
        .chip:hover { background: rgba(255,230,0,.14); border-color: rgba(255,230,0,.6); }
        .chip:nth-child(1) { animation-delay: .10s; }
        .chip:nth-child(2) { animation-delay: .16s; }
        .chip:nth-child(3) { animation-delay: .22s; }
        .chip:nth-child(4) { animation-delay: .28s; }
        .chip:nth-child(5) { animation-delay: .34s; }

        /* Bordered containers (how-it-works cards, nav cards, chart cards,
           summary card) lift on hover like the KPI cards do */
        [data-testid="stVerticalBlockBorderWrapper"] {
            transition: transform .18s ease, box-shadow .18s ease;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 26px rgba(0,0,0,.45);
        }

        /* All buttons get a gentle yellow edge on hover */
        .stButton button { transition: border-color .2s ease, transform .15s ease; }
        .stButton button:hover:enabled {
            border-color: rgba(255,230,0,.55);
            transform: translateY(-1px);
        }

        /* Dropzone breathes softly until interacted with */
        @keyframes borderPulse {
            0%, 100% { border-color: #3E3E4A; }
            50%      { border-color: rgba(255,230,0,.4); }
        }
        [data-testid="stFileUploaderDropzone"] { animation: borderPulse 3.2s ease-in-out infinite; }

        /* Softer horizontal rules */
        hr { border-color: #2A2A34; }

        /* Upload → Discover → Deep Dive stepper (vertical, lives in the sidebar) */
        .stepper-v { display: flex; flex-direction: column; gap: 4px; margin-top: 6px; }
        .stepper-v .label {
            color: #9A9AA6; font-size: .68rem; font-weight: 700;
            text-transform: uppercase; letter-spacing: .08em; margin-bottom: 6px;
        }
        .step {
            padding: 8px 14px; border-radius: 8px; font-size: .84rem; font-weight: 600;
            color: #9A9AA6; border: 1px solid #34343F; text-align: center;
        }
        .step.active {
            color: #F2F2F5; border-color: rgba(255,230,0,.6); background: rgba(255,230,0,.07);
            box-shadow: 0 0 14px rgba(255,230,0,.12);
        }
        .step-arrow-v { color: #5A5A66; text-align: center; font-size: .8rem; line-height: 1.2; }

        /* ═══════════ AESTHETIC OVERHAUL — glass, glow, colour ═══════════ */

        /* Glass top bar: the header (logo + nav tabs) floats on a blurred pane */
        header[data-testid="stHeader"] {
            background: rgba(20,20,27,.72) !important;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-bottom: 1px solid rgba(255,255,255,.06);
        }
        header[data-testid="stHeader"] a:hover {
            background: rgba(255,255,255,.05);
            border-radius: 8px;
        }
        [data-testid="stToolbar"] { opacity: .35; transition: opacity .2s ease; }
        [data-testid="stToolbar"]:hover { opacity: 1; }

        /* Bordered containers become glass panels */
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: linear-gradient(180deg, rgba(37,37,48,.55), rgba(26,26,34,.55));
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            border: 1px solid rgba(255,255,255,.07) !important;
            border-radius: 14px !important;
        }

        /* KPI cards: rounded top (surface + accent glow come from inline styles) */
        .kpi-card { border-radius: 10px 10px 0 0 !important; }

        /* Secondary buttons: glassy, rounded */
        .stButton button {
            background: rgba(255,255,255,.03);
            border: 1px solid rgba(255,255,255,.10);
            border-radius: 10px;
        }

        /* Hero accent: animated shimmer sweeping through the gradient */
        @keyframes shimmer { to { background-position: 200% center; } }
        .hero-title { font-size: 2.7rem; }
        .hero-title .accent {
            background: linear-gradient(90deg, #FFE600 0%, #FFC300 35%,
                        #FFF7B0 50%, #FFE600 65%, #FFC300 100%);
            background-size: 200% auto;
            -webkit-background-clip: text; background-clip: text; color: transparent;
            animation: shimmer 5s linear infinite;
        }

        /* Chat messages become soft bubbles */
        [data-testid="stChatMessage"] {
            background: rgba(255,255,255,.025);
            border: 1px solid rgba(255,255,255,.05);
            border-radius: 14px;
            padding: 10px 14px;
        }

        /* The AI-insight modal: elevated glass panel */
        div[role="dialog"] {
            background: #1B1B24 !important;
            border: 1px solid rgba(255,255,255,.09);
            border-radius: 16px;
            box-shadow: 0 24px 70px rgba(0,0,0,.6), 0 0 40px rgba(255,230,0,.05);
        }

        /* Toasts pick up the brand edge */
        [data-testid="stToast"] {
            background: #1E1E28;
            border: 1px solid rgba(255,230,0,.3);
            border-left: 4px solid #FFE600;
            border-radius: 10px;
        }

        /* Inputs: soft yellow focus ring */
        [data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within {
            box-shadow: 0 0 0 3px rgba(255,230,0,.22);
            border-radius: 8px;
        }

        /* Dataframes: rounded, framed */
        [data-testid="stDataFrame"] {
            border: 1px solid rgba(255,255,255,.07);
            border-radius: 10px;
            overflow: hidden;
        }

        /* Gradient hairline dividers */
        hr {
            border: none; height: 1px;
            background: linear-gradient(90deg, transparent,
                        rgba(255,255,255,.14), transparent);
        }

        /* Slim custom scrollbar */
        ::-webkit-scrollbar { width: 10px; height: 10px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #2E2E3A; border-radius: 6px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(255,230,0,.45); }

        /* Text selection in brand yellow */
        ::selection { background: rgba(255,230,0,.35); }

        /* Sidebar: glass over the gradient */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(28,28,38,.92), rgba(20,20,28,.92)) !important;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
        }

        /* ═══════ CUSTOM CARD SYSTEM (Page 1) — pure HTML, no Streamlit DOM ═══════ */

        /* Badge pill above the hero title */
        .hero-badge {
            display: inline-flex; align-items: center; gap: 8px;
            padding: 6px 16px; border-radius: 999px; margin-bottom: 16px;
            font-size: .72rem; font-weight: 700; letter-spacing: .14em;
            color: #FFE600; background: rgba(255,230,0,.08);
            border: 1px solid rgba(255,230,0,.35);
            animation: fadeUp .4s ease both;
        }

        /* How-it-works: gradient-border cards with ghost step numerals */
        .hw-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
        .hw-card {
            position: relative; overflow: hidden; padding: 22px 20px 20px;
            border-radius: 16px; border: 1px solid transparent;
            background:
                linear-gradient(rgba(27,27,37,.92), rgba(21,21,29,.92)) padding-box,
                linear-gradient(150deg, rgba(255,255,255,.16), rgba(255,255,255,.03) 40%,
                                var(--edge, rgba(124,92,255,.28))) border-box;
            animation: fadeUp .5s ease both; animation-delay: var(--d, 0s);
            transition: transform .2s ease, box-shadow .2s ease;
        }
        .hw-card:hover { transform: translateY(-5px); box-shadow: 0 14px 34px rgba(0,0,0,.5); }
        .hw-num {
            position: absolute; top: 6px; right: 16px;
            font-size: 2.8rem; font-weight: 800; color: rgba(255,255,255,.05);
            user-select: none;
        }
        .card-icon {
            width: 46px; height: 46px; border-radius: 12px;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.3rem; margin-bottom: 12px;
            background: radial-gradient(circle at 30% 30%, var(--ic1), var(--ic2));
            box-shadow: 0 4px 18px var(--glow);
        }
        .hw-title { font-weight: 800; color: #F2F2F5; font-size: 1.02rem; margin-bottom: 6px; }
        .hw-text { color: #9A9AA6; font-size: .88rem; line-height: 1.55; }

        /* Destination cards: whole card is a link, colour-coded per page,
           gradient border, glow, and a sheen that sweeps across on hover */
        .dest-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
        .dest-card {
            position: relative; display: block; overflow: hidden;
            padding: 24px 24px 22px; border-radius: 18px;
            border: 1px solid transparent; text-decoration: none !important;
            background:
                linear-gradient(rgba(25,25,34,.95), rgba(19,19,25,.95)) padding-box,
                linear-gradient(135deg, var(--edge1), rgba(255,255,255,.05) 45%, var(--edge2)) border-box;
            animation: fadeUp .5s ease both; animation-delay: var(--d, 0s);
            transition: transform .22s ease, box-shadow .22s ease;
        }
        .dest-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 18px 44px rgba(0,0,0,.55), 0 0 34px var(--halo);
        }
        .dest-card::after {
            content: ""; position: absolute; top: 0; left: -75%;
            width: 50%; height: 100%; transform: skewX(-18deg);
            background: linear-gradient(105deg, transparent, rgba(255,255,255,.07), transparent);
            transition: left .55s ease;
        }
        .dest-card:hover::after { left: 125%; }
        .dest-head { display: flex; align-items: center; gap: 14px; }
        .dest-head .card-icon { margin-bottom: 0; width: 50px; height: 50px; font-size: 1.45rem; }
        .dest-title { font-size: 1.22rem; font-weight: 800; color: #F2F2F5; }
        .dest-sub { color: #9A9AA6; margin-top: 12px; line-height: 1.6; font-size: .93rem; }
        .dest-cta {
            margin-top: 16px; display: inline-flex; align-items: center; gap: 8px;
            font-weight: 700; font-size: .92rem; color: var(--cta);
        }
        .dest-cta .arrow { transition: transform .2s ease; }
        .dest-card:hover .dest-cta .arrow { transform: translateX(6px); }
        .dest-lock {
            margin-top: 16px; display: inline-flex; align-items: center; gap: 8px;
            padding: 6px 14px; border-radius: 999px;
            font-size: .78rem; font-weight: 600; color: #8A8A96;
            background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.09);
        }
        .dest-card.locked { filter: saturate(.6); }
        .dest-card.locked:hover { transform: none; box-shadow: none; }

        /* Roomier upload dropzone */
        [data-testid="stFileUploaderDropzone"] { padding: 26px 22px; background: rgba(255,255,255,.015); }

        /* ═══════ FULL REVAMP LAYER — aurora, colour identities, glass ═══════ */

        html { scroll-behavior: smooth; }

        /* Living aurora: four blurred colour fields drifting slowly behind the
           whole app. Painted before (under) all content, pointer-events off. */
        @keyframes aurora {
            0%   { transform: translate(0, 0) scale(1); }
            50%  { transform: translate(-4%, 3%) scale(1.08); }
            100% { transform: translate(3%, -3%) scale(1.03); }
        }
        [data-testid="stAppViewContainer"]::before {
            content: ""; position: fixed; inset: -25%;
            z-index: 0; pointer-events: none;
            background:
                radial-gradient(38% 30% at 18% 22%, rgba(255,230,0,.10), transparent 70%),
                radial-gradient(34% 28% at 82% 16%, rgba(139,92,246,.11), transparent 70%),
                radial-gradient(40% 34% at 70% 84%, rgba(34,150,255,.09), transparent 70%),
                radial-gradient(26% 22% at 26% 80%, rgba(255,64,129,.06), transparent 70%);
            filter: blur(70px);
            animation: aurora 34s ease-in-out infinite alternate;
        }

        /* Page titles: soft white→silver gradient text */
        h1 {
            background: linear-gradient(90deg, #FFFFFF 0%, #C6C6D4 100%);
            -webkit-background-clip: text; background-clip: text; color: transparent;
        }

        /* Plotly charts as glass cards — stPlotlyChart is the chart's own stable
           element, so this works without relying on container internals */
        [data-testid="stPlotlyChart"] {
            background: linear-gradient(165deg, rgba(34,34,46,.85), rgba(22,22,30,.85));
            border: 1px solid rgba(255,255,255,.07);
            border-radius: 16px;
            padding: 12px 12px 4px;
            box-shadow: 0 8px 26px rgba(0,0,0,.35);
            transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
        }
        [data-testid="stPlotlyChart"]:hover {
            transform: translateY(-3px);
            border-color: rgba(255,230,0,.3);
            box-shadow: 0 14px 34px rgba(0,0,0,.5);
        }

        /* Section headers with per-section colour identity: icon medallion +
           gradient underline, driven by --acc set inline per section */
        .sec-h {
            display: flex; align-items: center; gap: 12px;
            position: relative; padding-bottom: 10px; margin: 6px 0 14px;
        }
        .sec-h::after {
            content: ""; position: absolute; left: 0; bottom: 0;
            height: 3px; width: 64px; border-radius: 2px;
            background: linear-gradient(90deg, var(--acc), transparent);
        }
        .sec-ic {
            width: 34px; height: 34px; border-radius: 10px; flex: 0 0 34px;
            display: flex; align-items: center; justify-content: center; font-size: 1.05rem;
            background: color-mix(in srgb, var(--acc) 16%, #1E1E28);
            border: 1px solid color-mix(in srgb, var(--acc) 45%, transparent);
            box-shadow: 0 3px 14px color-mix(in srgb, var(--acc) 22%, transparent);
        }
        .sec-t { font-size: 1.26rem; font-weight: 800; color: #F2F2F5; letter-spacing: -.01em; }
        .sec-n { color: #9A9AA6; font-weight: 600; font-size: .95rem; }

        /* Executive summary: tri-colour gradient border card */
        .exec-banner {
            position: relative; border-radius: 14px; padding: 16px 20px; margin: 6px 0 10px;
            border: 1px solid transparent;
            background:
                linear-gradient(rgba(26,26,36,.94), rgba(20,20,28,.94)) padding-box,
                linear-gradient(120deg, rgba(255,230,0,.55), rgba(151,124,255,.4) 50%,
                                rgba(64,160,255,.45)) border-box;
            color: #D8D8E2; line-height: 1.65;
            animation: fadeUp .5s ease both;
        }
        .exec-banner b { color: #F2F2F5; }

        /* Destination cards: equal heights regardless of text length */
        .dest-card { min-height: 212px; }

        /* Sidebar workflow panel gets its own glass card */
        .stepper-v {
            background: rgba(255,255,255,.025);
            border: 1px solid rgba(255,255,255,.07);
            border-radius: 14px; padding: 14px;
        }

        /* Destination CTAs (st.page_link under each card) as premium buttons */
        [data-testid="stPageLink"] a {
            display: flex; justify-content: center;
            padding: 10px 14px; border-radius: 10px;
            background: rgba(255,255,255,.03);
            border: 1px solid rgba(255,255,255,.14);
            font-weight: 700; text-decoration: none !important;
            transition: border-color .2s ease, transform .15s ease, box-shadow .2s ease;
        }
        [data-testid="stPageLink"] a p { font-weight: 700; }
        [data-testid="stPageLink"] a:hover {
            border-color: rgba(255,230,0,.6);
            transform: translateY(-1px);
            box-shadow: 0 6px 20px rgba(255,230,0,.10);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def stepper(active: int):
    """
    The Upload → Discover → Deep Dive flow indicator, rendered as a vertical
    panel in the left sidebar (same place the old page tabs used to live).
    Call once per page with `active` = 1, 2 or 3.
    """
    steps = ["1 · Upload", "2 · Discover", "3 · Deep Dive"]
    parts = ["<div class='label'>Workflow</div>"]
    for i, label in enumerate(steps, start=1):
        cls = "step active" if i == active else "step"
        parts.append(f"<div class='{cls}'>{label}</div>")
        if i < len(steps):
            parts.append("<div class='step-arrow-v'>↓</div>")
    with st.sidebar:
        st.markdown(f"<div class='stepper-v'>{''.join(parts)}</div>", unsafe_allow_html=True)


def section_header(icon: str, title: str, accent: str, note: str = ""):
    """
    A section heading with its own colour identity: a glowing icon medallion,
    the title, an optional muted note (e.g. a count), and a gradient underline
    in the section's accent colour. Gives each part of a page a distinct hue
    instead of one uniform yellow.
    """
    note_html = f"<span class='sec-n'>{note}</span>" if note else ""
    st.markdown(
        f"<div class='sec-h' style='--acc:{accent}'>"
        f"<span class='sec-ic'>{icon}</span>"
        f"<span class='sec-t'>{title}</span>{note_html}</div>",
        unsafe_allow_html=True,
    )
