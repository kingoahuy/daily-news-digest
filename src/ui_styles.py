from html import escape

import streamlit as st


SHADCN_STREAMLIT_CSS = """
<style>
:root {
    --background: #ffffff;
    --foreground: #020817;
    --muted: #f8fafc;
    --muted-foreground: #64748b;
    --card: #ffffff;
    --card-foreground: #020817;
    --border: #e2e8f0;
    --input: #e2e8f0;
    --primary: #0f172a;
    --primary-foreground: #f8fafc;
    --secondary: #f1f5f9;
    --secondary-foreground: #0f172a;
    --accent: #f1f5f9;
    --accent-foreground: #0f172a;
    --destructive: #ef4444;
    --destructive-foreground: #f8fafc;
    --ring: #94a3b8;
    --radius: 0.75rem;
    --card-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    --card-shadow-hover: 0 4px 12px rgba(15, 23, 42, 0.06);
}

* {
    box-sizing: border-box;
}

html, body, .stApp, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
        "SF Pro Text", "PingFang SC", "Hiragino Sans GB",
        "Microsoft YaHei", "Segoe UI", sans-serif;
    color: var(--foreground);
}

html, body, .stApp {
    background: var(--muted);
}

.block-container {
    max-width: 1160px;
    padding: 1.5rem 1.25rem 4rem;
}

h1 {
    margin-bottom: 0.35rem !important;
    font-size: 1.75rem !important;
    font-weight: 700 !important;
    line-height: 1.2 !important;
    letter-spacing: -0.025em;
}

h2 {
    font-size: 1.35rem !important;
    line-height: 1.35 !important;
}

h3 {
    font-size: 1rem !important;
    font-weight: 650 !important;
    line-height: 1.4 !important;
}

p, li, span, div, a, code {
    max-width: 100%;
}

a {
    color: #2563eb;
    overflow-wrap: anywhere;
    word-break: break-word;
}

.shad-card,
.news-title,
.news-summary,
.shad-card-description,
.stMarkdown,
.stDataFrame,
a {
    max-width: 100%;
    overflow-wrap: anywhere;
    word-break: break-word;
}

.shad-card {
    overflow: hidden;
    padding: 1rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--card);
    color: var(--card-foreground);
    box-shadow: var(--card-shadow);
    transition: border-color 140ms ease, box-shadow 140ms ease;
}

.shad-card:hover {
    border-color: #cbd5e1;
    box-shadow: var(--card-shadow-hover);
}

.shad-card-header {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    min-width: 0;
    margin-bottom: 0.75rem;
}

.shad-card-title {
    color: var(--foreground);
    font-size: 1rem;
    font-weight: 650;
    line-height: 1.4;
}

.shad-card-description {
    color: var(--muted-foreground);
    font-size: 0.875rem;
    line-height: 1.5;
}

.shad-card-content {
    color: var(--card-foreground);
    font-size: 0.875rem;
    line-height: 1.7;
}

.shad-card-footer {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 0.875rem;
    padding-top: 0.75rem;
    border-top: 1px solid var(--border);
}

.shad-hero {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 1rem;
    align-items: center;
    margin-bottom: 1rem;
    padding: 1.35rem 1.5rem;
}

.shad-hero-title {
    margin: 0 0 0.35rem;
    color: var(--foreground);
    font-size: 1.75rem;
    font-weight: 700;
    line-height: 1.2;
    letter-spacing: -0.025em;
}

.shad-hero-description {
    margin: 0;
    color: var(--muted-foreground);
    font-size: 0.9rem;
    line-height: 1.6;
}

.shad-hero-meta {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.45rem;
    min-width: 180px;
}

.shad-meta-line {
    color: var(--muted-foreground);
    font-size: 0.75rem;
    line-height: 1.4;
    text-align: right;
}

.shad-metric-card {
    min-height: 108px;
    padding: 0.95rem 1rem;
}

.shad-metric-label {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    color: var(--muted-foreground);
    font-size: 0.75rem;
    font-weight: 500;
    line-height: 1.35;
}

.shad-metric-value {
    margin: 0.45rem 0 0.2rem;
    color: var(--foreground);
    font-size: 1.25rem;
    font-weight: 700;
    line-height: 1.2;
}

.shad-metric-note {
    color: var(--muted-foreground);
    font-size: 0.75rem;
    line-height: 1.4;
}

.shad-nav-card {
    min-height: 112px;
}

.shad-nav-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.9rem;
    height: 1.9rem;
    margin-bottom: 0.65rem;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) - 2px);
    background: var(--secondary);
    color: var(--secondary-foreground);
    font-size: 0.9rem;
}

.shad-section-heading {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1rem;
    margin: 1.25rem 0 0.7rem;
}

.shad-section-title {
    color: var(--foreground);
    font-size: 1rem;
    font-weight: 650;
    line-height: 1.4;
}

.shad-section-description,
.page-description,
.shad-muted {
    color: var(--muted-foreground);
    font-size: 0.8125rem;
    line-height: 1.55;
}

.page-description {
    margin: 0;
}

.shad-badge-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 0.375rem;
    align-items: center;
    min-width: 0;
}

.shad-badge {
    display: inline-flex;
    align-items: center;
    max-width: 100%;
    min-height: 1.5rem;
    overflow: hidden;
    padding: 0.125rem 0.5rem;
    border: 1px solid transparent;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 500;
    line-height: 1.25rem;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.shad-badge-primary {
    background: var(--primary);
    color: var(--primary-foreground);
}

.shad-badge-secondary {
    background: var(--secondary);
    color: var(--secondary-foreground);
}

.shad-badge-outline {
    border-color: var(--border);
    background: transparent;
    color: var(--foreground);
}

.shad-badge-muted {
    background: var(--muted);
    color: var(--muted-foreground);
}

.shad-badge-success {
    border-color: #bbf7d0;
    background: #f0fdf4;
    color: #166534;
}

.shad-badge-warning {
    border-color: #fde68a;
    background: #fffbeb;
    color: #92400e;
}

.news-card-header {
    margin-bottom: 0.25rem;
}

.news-title {
    margin: 0.65rem 0 0.25rem;
    color: var(--foreground);
    font-size: 1rem;
    font-weight: 650;
    line-height: 1.45;
    white-space: normal;
}

.news-summary {
    margin: 0.7rem 0;
    color: #334155;
    font-size: 0.875rem;
    line-height: 1.7;
    white-space: normal;
}

.news-meta,
.status-line,
.cluster-line {
    color: var(--muted-foreground);
    font-size: 0.75rem;
    line-height: 1.5;
}

.news-source-link {
    display: inline-flex;
    margin-top: 0.2rem;
    font-size: 0.8125rem;
    font-weight: 500;
}

.ai-reason {
    margin: 0.55rem 0;
    padding: 0.75rem;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) - 2px);
    background: var(--muted);
    color: #334155;
    font-size: 0.875rem;
    line-height: 1.65;
}

.shad-alert {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 0.75rem;
    align-items: start;
    margin-bottom: 1rem;
    padding: 0.875rem 1rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--card);
    color: var(--foreground);
    box-shadow: var(--card-shadow);
}

.shad-alert-icon {
    color: var(--muted-foreground);
    font-size: 0.95rem;
    line-height: 1.4;
}

.shad-alert-title {
    margin-bottom: 0.15rem;
    font-size: 0.875rem;
    font-weight: 650;
}

.shad-alert-description {
    color: var(--muted-foreground);
    font-size: 0.8125rem;
    line-height: 1.55;
}

.shad-empty {
    padding: 2.25rem 1.25rem;
    border: 1px dashed var(--border);
    border-radius: var(--radius);
    background: var(--card);
    text-align: center;
}

.shad-empty-icon {
    margin-bottom: 0.65rem;
    color: var(--muted-foreground);
    font-size: 1.4rem;
}

.shad-empty-title {
    margin-bottom: 0.25rem;
    color: var(--foreground);
    font-size: 0.95rem;
    font-weight: 650;
}

.shad-empty-description {
    max-width: 520px;
    margin: 0 auto;
    color: var(--muted-foreground);
    font-size: 0.8125rem;
    line-height: 1.55;
}

div[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stForm"] {
    overflow: hidden;
    max-width: 100%;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    background: var(--card);
    box-shadow: var(--card-shadow);
}

div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: var(--card-shadow-hover);
}

div[data-testid="stMetric"] {
    padding: 0.9rem 1rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--card);
    box-shadow: var(--card-shadow);
}

div[data-testid="stMetricLabel"] {
    color: var(--muted-foreground);
    font-size: 0.75rem;
}

div[data-testid="stMetricValue"] {
    color: var(--foreground);
    font-size: 1.2rem;
}

.stButton > button,
.stDownloadButton > button,
button[data-testid="stBaseButton-secondary"],
button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-tertiary"] {
    min-height: 2.25rem;
    height: auto;
    padding: 0.4rem 0.875rem;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) - 2px);
    background: var(--background);
    color: var(--foreground);
    font-size: 0.875rem;
    font-weight: 500;
    line-height: 1.25rem;
    box-shadow: none;
}

.stButton > button:hover,
.stDownloadButton > button:hover,
button[data-testid="stBaseButton-secondary"]:hover {
    border-color: var(--ring);
    background: var(--accent);
    color: var(--accent-foreground);
}

button[kind="primary"],
button[data-testid="stBaseButton-primary"] {
    border-color: var(--primary);
    background: var(--primary);
    color: var(--primary-foreground);
}

button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover {
    border-color: #1e293b;
    background: #1e293b;
    color: var(--primary-foreground);
}

button[data-testid="stBaseButton-tertiary"] {
    border-color: transparent;
    background: transparent;
    color: var(--muted-foreground);
}

button[data-testid="stBaseButton-tertiary"]:hover {
    border-color: transparent;
    background: var(--accent);
    color: var(--foreground);
}

input, textarea, select, button, label {
    font-family: inherit !important;
}

input, textarea,
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div {
    border-color: var(--input) !important;
    border-radius: calc(var(--radius) - 2px) !important;
    background: var(--background) !important;
    color: var(--foreground) !important;
    font-size: 0.875rem !important;
    box-shadow: none !important;
}

input:focus, textarea:focus,
div[data-baseweb="select"] > div:focus-within,
div[data-baseweb="input"] > div:focus-within {
    border-color: var(--ring) !important;
    box-shadow: 0 0 0 2px rgba(148, 163, 184, 0.25) !important;
}

div[data-testid="stExpander"] {
    overflow: hidden;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) - 2px);
    background: var(--background);
}

div[data-testid="stAlert"] {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--card);
    color: var(--foreground);
}

div[data-testid="stDataFrame"],
div[data-testid="stTable"],
div[data-testid="stMarkdownContainer"] {
    max-width: 100%;
    overflow-x: auto;
    white-space: normal;
}

div[data-testid="stMarkdownContainer"] code,
div[data-testid="stMarkdownContainer"] pre {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    word-break: break-word;
}

@media (prefers-color-scheme: dark) {
    :root {
        --background: #020817;
        --foreground: #f8fafc;
        --muted: #0f172a;
        --muted-foreground: #94a3b8;
        --card: #0b1220;
        --card-foreground: #f8fafc;
        --border: #1e293b;
        --input: #334155;
        --primary: #f8fafc;
        --primary-foreground: #0f172a;
        --secondary: #1e293b;
        --secondary-foreground: #f8fafc;
        --accent: #1e293b;
        --accent-foreground: #f8fafc;
        --ring: #64748b;
    }

    .news-summary, .ai-reason {
        color: #cbd5e1;
    }

    .shad-badge-success {
        border-color: #166534;
        background: #052e16;
        color: #bbf7d0;
    }

    .shad-badge-warning {
        border-color: #92400e;
        background: #451a03;
        color: #fde68a;
    }
}

@media (max-width: 760px) {
    .block-container {
        padding: 1rem 0.75rem 3rem;
    }

    .shad-hero {
        grid-template-columns: 1fr;
        padding: 1.15rem;
    }

    .shad-hero-title {
        font-size: 1.5rem;
    }

    .shad-hero-meta {
        align-items: flex-start;
        min-width: 0;
    }

    .shad-meta-line {
        text-align: left;
    }

    .shad-metric-card {
        min-height: 96px;
    }
}
</style>
"""


def inject_shadcn_styles() -> None:
    st.markdown(SHADCN_STREAMLIT_CSS, unsafe_allow_html=True)


def clamp_text(text: object, max_chars: int = 180) -> str:
    value = " ".join(str(text or "").split())
    if len(value) <= max_chars:
        return value
    if max_chars <= 3:
        return value[:max_chars]
    return value[: max_chars - 3].rstrip() + "..."


def clamp_title(title: object, max_chars: int = 90) -> str:
    return clamp_text(title, max_chars)


def render_badge_html(text: object, variant: str = "secondary") -> str:
    allowed = {"primary", "secondary", "outline", "muted", "success", "warning"}
    safe_variant = variant if variant in allowed else "secondary"
    return (
        f'<span class="shad-badge shad-badge-{safe_variant}">'
        f"{escape(str(text))}</span>"
    )


def render_card_header_html(
    title: object,
    description: object = "",
    icon: object = "",
    action_html: str = "",
) -> str:
    icon_html = (
        f'<div class="shad-nav-icon">{escape(str(icon))}</div>'
        if icon
        else ""
    )
    description_html = (
        f'<div class="shad-card-description">{escape(str(description))}</div>'
        if description
        else ""
    )
    action = (
        f'<div class="shad-badge-wrap">{action_html}</div>'
        if action_html
        else ""
    )
    return (
        '<div class="shad-card-header">'
        f"{icon_html}"
        f'<div class="shad-card-title">{escape(str(title))}</div>'
        f"{description_html}{action}</div>"
    )


def render_metric_card_html(
    icon: object,
    label: object,
    value: object,
    note: object = "",
    badge_html: str = "",
) -> str:
    badge = (
        f'<div class="shad-badge-wrap">{badge_html}</div>'
        if badge_html
        else ""
    )
    return (
        '<div class="shad-card shad-metric-card">'
        f'<div class="shad-metric-label">{escape(str(icon))} '
        f"{escape(str(label))}</div>"
        f'<div class="shad-metric-value">{escape(str(value))}</div>'
        f'<div class="shad-metric-note">{escape(str(note))}</div>'
        f"{badge}</div>"
    )


def render_empty_state_html(
    title: object,
    description: object,
    icon: object = "·",
) -> str:
    return (
        '<div class="shad-empty">'
        f'<div class="shad-empty-icon">{escape(str(icon))}</div>'
        f'<div class="shad-empty-title">{escape(str(title))}</div>'
        f'<div class="shad-empty-description">'
        f"{escape(str(description))}</div></div>"
    )
