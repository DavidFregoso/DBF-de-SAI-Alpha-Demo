from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st

THEME_TOKENS: dict[str, dict[str, Any]] = {
    "light": {
        "name": "Claro",
        "bg": "#f7f7f9",
        "card": "#ffffff",
        "fg": "#111827",
        "muted": "#6b7280",
        "border": "rgba(0,0,0,.12)",
        "grid": "rgba(0,0,0,.10)",
        "accent": "#156f4c",
        "paper_bg": "#ffffff",
        "plot_bg": "#ffffff",
        "palette": [
            "#156f4c",
            "#1d4ed8",
            "#f97316",
            "#ef4444",
            "#7c3aed",
            "#0ea5e9",
            "#16a34a",
            "#d97706",
            "#be185d",
            "#334155",
        ],
    },
    "dark": {
        "name": "Oscuro",
        "bg": "#0b1220",
        "card": "#121a2a",
        "fg": "#e5e7eb",
        "muted": "#9ca3af",
        "border": "rgba(255,255,255,.12)",
        "grid": "rgba(255,255,255,.12)",
        "accent": "#33c28a",
        "paper_bg": "#121a2a",
        "plot_bg": "#121a2a",
        "palette": [
            "#33c28a",
            "#5aa7ff",
            "#ff9f40",
            "#ff6b6b",
            "#c77dff",
            "#f7b801",
            "#2ec4b6",
            "#e36414",
            "#90be6d",
            "#4d908e",
        ],
    },
}


def _normalize_theme(theme: str | None, default: str = "dark") -> str:
    normalized = (theme or "").strip().lower()
    if normalized in {"light", "dark"}:
        return normalized
    return default


def get_theme_config(theme: str) -> dict[str, Any]:
    normalized = _normalize_theme(theme)
    tokens = THEME_TOKENS[normalized]
    return {
        "name": tokens["name"],
        "bg": tokens["bg"],
        "panel": tokens["card"],
        "text": tokens["fg"],
        "muted": tokens["muted"],
        "grid": tokens["grid"],
        "accent": tokens["accent"],
        "palette": tokens["palette"],
    }


def init_theme_state(default: str = "dark") -> None:
    theme_param = st.query_params.get("theme")
    if isinstance(theme_param, list):
        theme_param = theme_param[0] if theme_param else None

    if isinstance(theme_param, str) and theme_param.strip().lower() in {"light", "dark"}:
        st.session_state["theme"] = theme_param.strip().lower()
    elif "theme" not in st.session_state:
        st.session_state["theme"] = _normalize_theme(default)

    st.query_params["theme"] = st.session_state["theme"]


def set_theme(theme: str) -> None:
    normalized = (theme or "").strip().lower()
    if normalized not in {"light", "dark"}:
        raise ValueError("theme must be 'light' or 'dark'")
    st.session_state["theme"] = normalized
    st.query_params["theme"] = normalized
    st.rerun()


def apply_theme_css(theme: str) -> None:
    normalized = _normalize_theme(theme)
    tokens = THEME_TOKENS[normalized]
    accent = st.session_state.get("theme_accent", tokens["accent"])

    density = st.session_state.get("table_density", "Confortable")
    st.session_state["sidebar_header_rendered"] = False
    row_height = {"Compacta": 26, "Confortable": 34, "Amplia": 42}.get(density, 34)
    st.session_state["row_height"] = row_height

    st.session_state["theme_cfg"] = get_theme_config(normalized)
    st.session_state["plotly_colors"] = tokens["palette"]

    st.markdown(
        f"""
        <style>
            :root {{
                color-scheme: {normalized};
                --bg: {tokens["bg"]};
                --card: {tokens["card"]};
                --fg: {tokens["fg"]};
                --muted: {tokens["muted"]};
                --border: {tokens["border"]};
                --accent: {accent};
            }}

            #MainMenu {{ visibility: hidden; }}
            header {{ visibility: hidden; }}
            footer {{ visibility: hidden; }}
            [data-testid="stToolbar"] {{ visibility: hidden; height: 0; }}
            [data-testid="stStatusWidget"] {{ visibility: hidden; }}
            [data-testid="stDecoration"] {{ visibility: hidden; }}
            [data-testid="stDeployButton"] {{ display: none; }}

            body,
            .stApp,
            [data-testid="stAppViewContainer"] {{
                background-color: var(--bg) !important;
                color: var(--fg) !important;
            }}

            [data-testid="stAppViewContainer"] * {{
                color: var(--fg);
            }}

            input,
            textarea {{
                -webkit-text-fill-color: var(--fg) !important;
            }}

            [data-testid="stHeader"],
            [data-testid="stToolbar"] {{
                background: var(--bg);
                color: var(--fg);
            }}

            section[data-testid="stSidebar"] {{
                background: var(--bg) !important;
                min-width: 360px;
                width: 360px;
            }}
            section[data-testid="stSidebar"] > div {{
                min-width: 360px;
                width: 360px;
            }}
            section[data-testid="stSidebar"] * {{
                color: var(--fg) !important;
            }}

            [data-testid="stMarkdownContainer"],
            [data-testid="stMetricValue"],
            [data-testid="stMetricLabel"] {{
                color: var(--fg);
            }}

            .app-header {{
                font-weight: 700;
                font-size: 1.4rem;
                color: var(--accent);
                margin-bottom: 0.25rem;
            }}
            .app-subtitle {{
                color: var(--muted);
                margin-top: 0;
            }}
            .top-header {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1rem;
                padding: 0.75rem 1rem;
                border-radius: 12px;
                background: var(--card);
                border: 1px solid var(--border);
                margin-bottom: 1.5rem;
            }}
            .top-header-title {{
                font-weight: 700;
                font-size: 1.3rem;
                color: var(--accent);
            }}
            .top-header-sub {{
                color: var(--muted);
                font-size: 0.9rem;
                margin-top: 0.15rem;
            }}
            .status-pills {{
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                justify-content: flex-end;
            }}
            .status-pill {{
                background: var(--bg);
                border: 1px solid var(--border);
                border-radius: 999px;
                padding: 0.35rem 0.75rem;
                font-size: 0.8rem;
                color: var(--fg);
                box-shadow: 0 1px 2px rgba(0,0,0,0.04);
            }}
            .refresh-box {{
                display: flex;
                flex-direction: column;
                align-items: flex-end;
                gap: 0.35rem;
            }}
            .refresh-label {{
                color: var(--muted);
                font-size: 0.8rem;
            }}
            [data-testid="stMetricValue"] {{
                color: var(--accent);
            }}
            [data-testid="stMetricDelta"] {{
                color: var(--accent);
            }}
            [data-testid="stMetricLabel"] {{
                color: var(--muted);
            }}
            .section-title {{
                border-left: 4px solid var(--accent);
                padding-left: 0.6rem;
                font-weight: 600;
                font-size: 1.1rem;
                color: var(--fg);
            }}
            .sidebar-title {{
                font-weight: 700;
                font-size: 1.05rem;
                color: var(--accent);
                margin-bottom: 0.1rem;
            }}
            .sidebar-subtitle {{
                color: var(--muted);
                font-size: 0.85rem;
                margin-top: 0;
            }}
            .sidebar-theme {{
                color: var(--fg);
                font-size: 0.8rem;
                margin-top: 0.35rem;
                margin-bottom: 0.1rem;
            }}

            [data-testid="stDateInput"] {{
                width: 100%;
            }}
            [data-testid="stDateInput"] > div {{
                width: 100%;
            }}

            [data-testid="stDataFrame"] {{
                background: var(--card);
                border: 1px solid var(--border);
                color: var(--fg);
            }}
            [data-testid="stDataFrame"] thead tr th {{
                background: var(--bg);
                color: var(--fg);
                border-bottom: 1px solid var(--border);
            }}
            [data-testid="stDataFrame"] tbody tr td {{
                color: var(--fg);
                border-bottom: 1px solid var(--border);
            }}

            .stSelectbox > div > div,
            .stMultiSelect > div > div,
            .stTextInput > div > div,
            .stDateInput > div > div {{
                background-color: var(--card);
                color: var(--fg);
                border-color: var(--border);
            }}

            button,
            button * {{
                color: var(--fg) !important;
            }}
            button {{
                background: var(--card) !important;
                border: 1px solid var(--border) !important;
                box-shadow: none !important;
            }}
            [data-testid="baseButton-primary"] button {{
                background: var(--accent) !important;
                color: white !important;
            }}
            button:hover {{
                filter: brightness(0.97);
            }}
            button:disabled {{
                opacity: .6;
            }}

            [data-testid="stButton"] > button,
            [data-testid="baseButton-primary"] > button,
            [data-testid="baseButton-secondary"] > button,
            [data-testid="stDownloadButton"] button,
            button[kind] {{
                background: var(--card) !important;
                border: 1px solid var(--border) !important;
                color: var(--fg) !important;
                box-shadow: none !important;
            }}

            div[data-baseweb="select"] > div,
            div[data-baseweb="input"] > div,
            div[data-baseweb="textarea"] > div {{
                background: var(--card) !important;
                border-color: var(--border) !important;
            }}
            div[data-baseweb="select"] * {{
                color: var(--fg) !important;
            }}
            div[data-baseweb="input"] input,
            div[data-baseweb="textarea"] textarea {{
                color: var(--fg) !important;
                -webkit-text-fill-color: var(--fg) !important;
                background: transparent !important;
            }}
            div[data-baseweb="input"] input::placeholder,
            div[data-baseweb="textarea"] textarea::placeholder {{
                color: var(--muted) !important;
            }}

            ul[role="listbox"],
            li[role="option"],
            [role="menu"] {{
                background: var(--card) !important;
                color: var(--fg) !important;
                border: 1px solid var(--border) !important;
            }}

            .stRadio div[role="radiogroup"] label,
            .stRadio div[role="radiogroup"] label span {{
                color: var(--fg) !important;
            }}

            [role="tablist"] button {{
                background: var(--card) !important;
                border: 1px solid var(--border) !important;
                color: var(--fg) !important;
            }}
            [role="tablist"] button[aria-selected="true"] {{
                background: var(--bg) !important;
                border-color: var(--accent) !important;
                color: var(--fg) !important;
            }}

            [data-testid="stSidebarNav"],
            [data-testid="stSidebarNavItems"],
            [data-testid="stSidebarNavSeparator"] {{
                display: none;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_plotly_template(theme: str) -> go.layout.Template:
    normalized = _normalize_theme(theme)
    tokens = THEME_TOKENS[normalized]
    return go.layout.Template(
        layout=go.Layout(
            paper_bgcolor=tokens["paper_bg"],
            plot_bgcolor=tokens["plot_bg"],
            font=dict(color=tokens["fg"]),
            colorway=tokens["palette"],
            xaxis=dict(
                gridcolor=tokens["grid"],
                zerolinecolor=tokens["grid"],
                linecolor=tokens["grid"],
            ),
            yaxis=dict(
                gridcolor=tokens["grid"],
                zerolinecolor=tokens["grid"],
                linecolor=tokens["grid"],
            ),
        )
    )
