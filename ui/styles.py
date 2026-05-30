"""
All CSS for the Streamlit UI.

Colors and fonts are driven by config.py — edit there, not here.
Call get_css() to get the full stylesheet string for st.markdown injection.
"""

from config import (
    COLOR_PRIMARY, COLOR_SECONDARY, COLOR_NAVY, COLOR_TEAL,
    COLOR_BG, COLOR_SURFACE, COLOR_BORDER,
    COLOR_TEXT_BODY, COLOR_TEXT_MUTED,
    COLOR_USER_MSG_BG, COLOR_USER_MSG_BORDER,
    COLOR_CT_BG, COLOR_CT_TEXT, COLOR_CT_BORDER,
    COLOR_PM_BG, COLOR_PM_TEXT, COLOR_PM_BORDER,
    FONT_BODY, FONT_HEADING,
)


def get_css() -> str:
    return f"""
    <style>
    /* ── Global font — Arial/Calibri per Mayo brand ──────────────────────── */
    html, body, [class*="css"], .stMarkdown, button, input, textarea {{
        font-family: {FONT_BODY} !important;
    }}

    /* ── Mobile-First Light Theme Override ─────────────────────────────── */
    @media (max-width: 768px) {{
        html, body, [data-stale="false"] {{
            background-color: #ffffff !important;
            color: {COLOR_TEXT_BODY} !important;
        }}
        [data-testid="stApp"] {{
            background-color: {COLOR_BG} !important;
        }}
        *, *::before, *::after {{
            color: inherit !important;
        }}
    }}

    /* ── Enterprise ribbon ───────────────────────────────────────────────── */
    .ent-ribbon {{
        position: fixed; top: 0; left: 0; right: 0; height: 52px;
        background: {COLOR_PRIMARY};
        display: flex; align-items: center;
        justify-content: space-between; padding: 0 1.25rem;
        z-index: 10000; box-shadow: 0 1px 4px rgba(0,0,0,0.25);
        font-family: {FONT_BODY};
    }}
    .ent-ribbon-left {{ display: flex; align-items: center; gap: 1rem; }}
    .ent-brand {{
        font-size: 0.875rem; font-weight: 600; color: #f1f5f9;
        letter-spacing: -0.01em;
        font-family: {FONT_HEADING};
    }}
    [data-testid="stSidebar"] {{ top: 52px !important; }}

    /* ── Layout ──────────────────────────────────────────────────────────── */
    [data-testid="stMainBlockContainer"] {{
        max-width: 840px;
        margin: 0 auto;
        padding: 1.5rem 2rem 6rem;
    }}
    @media (max-width: 768px) {{
        [data-testid="stMainBlockContainer"] {{
            padding: 3rem 0.5rem 4rem;
            max-width: 100%;
        }}
    }}
    @media (max-width: 480px) {{
        [data-testid="stMainBlockContainer"] {{
            padding: 2.75rem 0.25rem 4rem;
        }}
    }}

    /* ── Background ───────────────────────────────────────────────────────── */
    [data-testid="stMain"] {{ background: {COLOR_BG}; }}
    @media (max-width: 768px) {{
        [data-testid="stMain"] {{ background: {COLOR_BG} !important; }}
    }}

    /* ── Workspace header ─────────────────────────────────────────────────── */
    .workspace-header {{ padding: 2rem 0 1.75rem; }}
    .greeting-text {{
        font-size: 2.2rem; font-weight: 700; color: {COLOR_NAVY};
        letter-spacing: -0.04em; line-height: 1.1; margin-bottom: 0.5rem;
        font-family: {FONT_HEADING};
    }}
    .greeting-sub {{
        font-size: 1rem; color: {COLOR_TEXT_MUTED}; font-weight: 400;
        font-family: {FONT_BODY};
    }}
    @media (max-width: 768px) {{
        .workspace-header {{ padding: 1.25rem 0 1rem; }}
        .greeting-text {{ font-size: 1.5rem; }}
        .greeting-sub {{ font-size: 0.875rem; }}
    }}

    /* ── Badges ───────────────────────────────────────────────────────────── */
    .badge {{
        display: inline-flex; align-items: center; gap: 5px;
        padding: 5px 12px; border-radius: 20px;
        font-size: 0.78rem; font-weight: 600; letter-spacing: 0.01em;
        font-family: {FONT_BODY};
    }}
    .badge-ct {{
        background: {COLOR_CT_BG}; color: {COLOR_CT_TEXT};
        border: 1px solid {COLOR_CT_BORDER};
    }}
    .badge-pm {{
        background: {COLOR_PM_BG}; color: {COLOR_PM_TEXT};
        border: 1px solid {COLOR_PM_BORDER};
    }}
    @media (max-width: 768px) {{
        .badge {{
            font-size: 0.7rem; padding: 4px 10px;
            background: #ffffff !important;
            border: 1.5px solid !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }}
        .badge-ct {{
            color: {COLOR_NAVY} !important;
            border-color: {COLOR_SECONDARY} !important;
        }}
        .badge-pm {{
            color: {COLOR_PM_TEXT} !important;
            border-color: {COLOR_TEAL} !important;
        }}
    }}
    @media (max-width: 480px) {{
        .badge {{ font-size: 0.65rem; padding: 3px 8px; }}
    }}

    /* ── Section label ────────────────────────────────────────────────────── */
    .section-label {{
        font-size: 0.68rem; font-weight: 700; letter-spacing: 0.1em;
        text-transform: uppercase; color: #a8a29e; margin: 1.5rem 0 0.75rem;
        font-family: {FONT_BODY};
    }}

    /* ── Example question buttons ─────────────────────────────────────────── */
    div[data-testid="column"] .stButton > button {{
        background: {COLOR_SURFACE}; border: 1px solid {COLOR_BORDER};
        border-radius: 14px; padding: 1rem 1.125rem;
        text-align: left; height: auto; min-height: 72px;
        font-size: 0.875rem; color: {COLOR_TEXT_BODY}; font-weight: 500;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05); transition: all 0.15s ease;
        white-space: normal; line-height: 1.5; width: 100%;
        font-family: {FONT_BODY};
    }}
    div[data-testid="column"] .stButton > button:hover {{
        border-color: {COLOR_SECONDARY}; background: #f0f4fb;
        box-shadow: 0 3px 10px rgba(14,50,147,0.08);
        transform: translateY(-1px); color: {COLOR_NAVY};
    }}
    @media (max-width: 768px) {{
        div[data-testid="column"] .stButton > button {{
            min-height: 56px; font-size: 0.82rem; padding: 0.75rem 0.875rem;
            border-radius: 10px; background: #ffffff !important;
            border: 1px solid {COLOR_BORDER} !important;
            color: {COLOR_TEXT_BODY} !important; margin-bottom: 0.5rem;
        }}
        div[data-testid="column"] .stButton > button:active {{
            background: #f0f4fb !important;
            border-color: {COLOR_SECONDARY} !important;
            transform: scale(0.98);
        }}
    }}
    @media (max-width: 480px) {{
        div[data-testid="column"] .stButton > button {{
            min-height: 52px; font-size: 0.78rem;
            padding: 0.625rem 0.75rem; border-radius: 8px;
        }}
    }}

    /* ── Message cards ────────────────────────────────────────────────────── */
    [data-testid="stChatMessage"] {{
        background: {COLOR_SURFACE}; border-radius: 16px;
        border: 1px solid {COLOR_BORDER};
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
        padding: 1rem 1.25rem !important; margin-bottom: 0.75rem;
    }}
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {{
        background: {COLOR_USER_MSG_BG}; border-color: {COLOR_USER_MSG_BORDER};
    }}
    @media (max-width: 768px) {{
        [data-testid="stChatMessage"] {{
            background: #ffffff !important;
            border: 1px solid {COLOR_BORDER} !important;
            border-radius: 12px;
            padding: 0.75rem 0.875rem !important;
            margin: 0 0.25rem 0.5rem 0.25rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }}
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {{
            background: #f8fafc !important;
            border-color: #cbd5e1 !important;
        }}
        [data-testid="stChatMessage"] * {{
            color: {COLOR_TEXT_BODY} !important;
        }}
        [data-testid="stChatMessage"] a {{
            color: {COLOR_PRIMARY} !important;
        }}
    }}
    @media (max-width: 480px) {{
        [data-testid="stChatMessage"] {{
            padding: 0.625rem 0.75rem !important;
            margin: 0 0.125rem 0.375rem 0.125rem;
            border-radius: 10px;
        }}
    }}

    /* ── Compact header ───────────────────────────────────────────────────── */
    .compact-header {{
        display: flex; align-items: center; gap: 0.625rem;
        padding: 0.25rem 0 0.875rem; flex-wrap: wrap;
    }}
    .compact-title {{
        font-size: 1.05rem; font-weight: 700; color: {COLOR_NAVY};
        letter-spacing: -0.015em; margin-right: 0.25rem;
        font-family: {FONT_HEADING};
    }}
    @media (max-width: 768px) {{
        .compact-header {{
            padding: 0.5rem 0.5rem 0.75rem;
            background: {COLOR_SURFACE};
            border-radius: 10px;
            margin: 0.25rem 0.25rem 0.75rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            border: 1px solid {COLOR_BORDER};
            gap: 0.5rem;
        }}
        .compact-title {{
            font-size: 0.9rem;
            color: {COLOR_TEXT_BODY} !important;
        }}
    }}
    @media (max-width: 480px) {{
        .compact-header {{
            padding: 0.375rem 0.5rem 0.5rem;
            margin: 0.125rem 0.125rem 0.5rem;
        }}
        .compact-title {{ font-size: 0.85rem; }}
    }}

    /* ── Tables in chat ───────────────────────────────────────────────────── */
    [data-testid="stChatMessage"] table {{
        display: block; overflow-x: auto; white-space: nowrap;
        border-collapse: collapse; font-size: 0.85rem; margin: 0.5rem 0;
    }}
    [data-testid="stChatMessage"] table th {{
        background: #f8fafc; padding: 7px 14px; text-align: left;
        font-weight: 600; font-size: 0.8rem; color: {COLOR_NAVY};
        border-bottom: 1.5px solid {COLOR_BORDER};
        font-family: {FONT_HEADING};
    }}
    [data-testid="stChatMessage"] table td {{
        padding: 7px 14px; border-bottom: 1px solid #f1f5f9;
        color: #334155;
    }}
    [data-testid="stChatMessage"] table tr:last-child td {{ border-bottom: none; }}

    /* ── Copy response block ──────────────────────────────────────────────── */
    [data-testid="stChatMessage"] [data-testid="stExpander"] pre {{
        background: #f8fafc !important; color: #475569 !important;
        font-family: inherit !important; font-size: 0.85rem !important;
        white-space: pre-wrap !important; word-break: break-word !important;
    }}

    /* ── Accessibility: visible focus states ─────────────────────────────── */
    a:focus-visible, button:focus-visible,
    [role="button"]:focus-visible, input:focus-visible, textarea:focus-visible {{
        outline: 2px solid {COLOR_PRIMARY} !important;
        outline-offset: 2px !important;
        border-radius: 4px;
    }}

    /* ── Toolbar hidden ───────────────────────────────────────────────────── */
    [data-testid="stToolbar"]   {{ display: none !important; }}
    [data-testid="stDecoration"] {{ display: none !important; }}

    /* ── Sidebar ──────────────────────────────────────────────────────────── */
    [data-testid="stSidebar"] {{
        background: #faf9f7; border-right: 1px solid #e8e5e0;
    }}
    @media (max-width: 768px) {{
        [data-testid="stSidebar"] {{
            background: #f8fafc !important;
            border-right: 1px solid {COLOR_BORDER} !important;
        }}
        [data-testid="stSidebar"] * {{
            color: {COLOR_TEXT_BODY} !important;
        }}
        [data-testid="stSidebar"] .stMarkdown h2 {{
            color: {COLOR_TEXT_BODY} !important;
            font-size: 1rem !important;
        }}
        [data-testid="stSidebar"] .stButton > button {{
            background: #ffffff !important;
            color: #374151 !important;
            border: 1px solid #d1d5db !important;
            font-size: 0.8rem !important;
        }}
        [data-testid="stSidebar"] .stDownloadButton > button {{
            background: {COLOR_PRIMARY} !important;
            color: #ffffff !important;
            border: none !important;
        }}
    }}

    /* ── Mobile input ─────────────────────────────────────────────────────── */
    @media (max-width: 768px) {{
        [data-testid="stChatInput"] {{
            background: #ffffff !important;
            border-radius: 12px !important;
            border: 1.5px solid #d1d5db !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
        }}
        [data-testid="stChatInput"] input {{
            color: {COLOR_TEXT_BODY} !important;
            font-size: 0.9rem !important;
            padding: 0.75rem !important;
            font-family: {FONT_BODY} !important;
        }}
        [data-testid="stChatInput"] input::placeholder {{
            color: #6b7280 !important;
        }}
        [data-testid="stChatInputContainer"] {{
            background: #f8fafc !important;
            padding: 0.75rem 0.5rem !important;
        }}
    }}

    /* ── Source pills ─────────────────────────────────────────────────────── */
    .source-pill {{
        display: inline-flex; align-items: center;
        padding: 3px 10px; border-radius: 20px;
        font-size: 0.72rem; font-weight: 600; margin-right: 4px;
        font-family: {FONT_BODY};
    }}
    .pill-ct {{
        background: {COLOR_CT_BG}; color: {COLOR_CT_TEXT};
        border: 1px solid {COLOR_CT_BORDER};
    }}
    .pill-pm {{
        background: {COLOR_PM_BG}; color: {COLOR_PM_TEXT};
        border: 1px solid {COLOR_PM_BORDER};
    }}
    @media (max-width: 768px) {{
        .source-pill {{
            background: #ffffff !important;
            border: 1px solid !important;
            font-size: 0.65rem; padding: 2px 8px;
        }}
        .pill-ct {{
            color: {COLOR_NAVY} !important;
            border-color: {COLOR_SECONDARY} !important;
        }}
        .pill-pm {{
            color: {COLOR_PM_TEXT} !important;
            border-color: {COLOR_TEAL} !important;
        }}
        [data-testid="stExpander"] {{
            background: #f8fafc !important;
            border: 1px solid {COLOR_BORDER} !important;
            border-radius: 8px !important;
        }}
        [data-testid="stExpander"] summary {{
            background: #ffffff !important;
            color: #374151 !important;
            font-size: 0.8rem !important;
            padding: 0.5rem !important;
        }}
        [data-testid="stExpander"] div {{
            background: #f8fafc !important;
            color: #4b5563 !important;
        }}
        [data-testid="stStatus"] {{
            background: #ffffff !important;
            border: 1px solid {COLOR_BORDER} !important;
            border-radius: 8px !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
        }}
        [data-testid="stStatus"] * {{
            color: #374151 !important;
        }}
    }}

    /* ── Sidebar enterprise elements ──────────────────────────────────────── */
    .src-status {{
        display: flex; align-items: center; gap: 0.5rem;
        padding: 0.25rem 0; font-size: 0.82rem;
    }}
    .src-dot  {{ color: #16a34a; font-size: 0.55rem; flex-shrink: 0; }}
    .src-name {{ color: #334155; font-weight: 500; flex: 1; }}
    .src-conn {{ color: #16a34a; font-size: 0.72rem; font-weight: 600; }}
    .hist-item {{
        font-size: 0.73rem; color: {COLOR_TEXT_MUTED};
        padding: 0.15rem 0.5rem;
        border-left: 2px solid {COLOR_BORDER};
        margin: 0.15rem 0;
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }}
    </style>
    """
