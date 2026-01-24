from __future__ import annotations

from typing import Any

import plotly.io as pio
import streamlit as st


def get_theme_config(theme_name: str) -> dict[str, Any]:
    normalized = (theme_name or "Claro").strip().lower()
    if normalized in {"oscuro", "dark"}:
        return {
            "name": "Oscuro",
            "bg": "#0f1116",
            "panel": "#1a202a",
            "text": "#f5f7fb",
            "muted": "#b6c2d0",
            "grid": "#2f3a49",
            "accent": "#33c28a",
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
            "plotly_template_name": "sai_alpha_dark",
        }
    return {
        "name": "Claro",
        "bg": "#f7f8fb",
        "panel": "#ffffff",
        "text": "#111111",
        "muted": "#64748b",
        "grid": "rgba(0,0,0,0.10)",
        "accent": "#156f4c",
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
        "plotly_template_name": "sai_alpha_light",
    }


def apply_theme_css(theme_cfg: dict[str, Any]) -> None:
    bg = theme_cfg["bg"]
    panel = theme_cfg["panel"]
    text = theme_cfg["text"]
    muted = theme_cfg["muted"]
    accent = theme_cfg["accent"]
    grid = theme_cfg["grid"]
    is_dark = theme_cfg["name"] == "Oscuro"
    hover_bg = "#1f2937" if is_dark else "rgba(15, 23, 42, 0.06)"
    tab_active_bg = "#111827" if is_dark else "rgba(15, 23, 42, 0.08)"
    st.markdown(
        f"""
        <style>
            :root {{
                color-scheme: { "dark" if is_dark else "light" };
                --bg: {bg};
                --fg: {text};
                --card: {panel};
                --border: {grid};
                --muted: {muted};
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
                background-color: var(--bg);
                color: var(--fg);
            }}

            [data-testid="stHeader"],
            [data-testid="stToolbar"] {{
                background: var(--bg);
                color: var(--fg);
            }}

            [data-testid="stAppViewContainer"] p,
            [data-testid="stAppViewContainer"] span,
            [data-testid="stAppViewContainer"] label,
            [data-testid="stAppViewContainer"] h1,
            [data-testid="stAppViewContainer"] h2,
            [data-testid="stAppViewContainer"] h3,
            [data-testid="stAppViewContainer"] h4,
            [data-testid="stAppViewContainer"] h5,
            [data-testid="stAppViewContainer"] h6,
            [data-testid="stMarkdownContainer"],
            [data-testid="stMetricValue"],
            [data-testid="stMetricLabel"],
            [data-testid="stSidebar"] .stMarkdown,
            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] .stCaption,
            [data-testid="stSidebar"] .stRadio,
            [data-testid="stSidebar"] .stSelectbox,
            [data-testid="stSidebar"] .stMultiSelect,
            [data-testid="stSidebar"] .stDateInput {{
                color: var(--fg);
            }}

            section[data-testid="stSidebar"] {{
                background-color: var(--bg) !important;
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

            [data-testid="stMarkdownContainer"] {{
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
            [data-testid="stDataFrame"] tbody tr:hover {{
                background: {hover_bg};
            }}

            .stSelectbox > div > div,
            .stMultiSelect > div > div,
            .stTextInput > div > div,
            .stDateInput > div > div {{
                background-color: var(--card);
                color: var(--fg);
                border-color: var(--border);
            }}

            [data-testid="stButton"] > button,
            [data-testid="baseButton-primary"] > button,
            [data-testid="baseButton-secondary"] > button,
            [data-testid="stDownloadButton"] button,
            button[kind],
            button {{
                background: var(--card) !important;
                border: 1px solid var(--border) !important;
                color: var(--fg) !important;
                box-shadow: none !important;
            }}
            button:hover,
            [data-testid="stButton"] > button:hover,
            [data-testid="baseButton-primary"] > button:hover,
            [data-testid="baseButton-secondary"] > button:hover,
            [data-testid="stDownloadButton"] button:hover {{
                background: {hover_bg} !important;
                color: var(--fg) !important;
            }}
            button *,
            [data-testid="stButton"] > button *,
            [data-testid="baseButton-primary"] > button *,
            [data-testid="baseButton-secondary"] > button *,
            [data-testid="stDownloadButton"] button * {{
                color: var(--fg) !important;
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
            li[role="option"] {{
                background: var(--card) !important;
                color: var(--fg) !important;
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
                background: {tab_active_bg} !important;
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


def apply_global_css(theme_cfg: dict[str, Any]) -> None:
    apply_theme_css(theme_cfg)


def apply_plotly_theme(theme_cfg: dict[str, Any]) -> None:
    template_name = theme_cfg["plotly_template_name"]
    is_light = theme_cfg["name"] == "Claro"
    paper_bg = "#ffffff" if is_light else theme_cfg["bg"]
    plot_bg = "#ffffff" if is_light else theme_cfg["panel"]
    pio.templates[template_name] = dict(
        layout=dict(
            colorway=theme_cfg["palette"],
            font=dict(family="Inter, sans-serif", color=theme_cfg["text"]),
            paper_bgcolor=paper_bg,
            plot_bgcolor=plot_bg,
            hovermode="x unified",
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=theme_cfg["text"])),
            xaxis=dict(
                showgrid=True,
                gridcolor=theme_cfg["grid"],
                zerolinecolor=theme_cfg["grid"],
                linecolor=theme_cfg["grid"],
                tickfont=dict(color=theme_cfg["text"]),
                titlefont=dict(color=theme_cfg["text"]),
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor=theme_cfg["grid"],
                zerolinecolor=theme_cfg["grid"],
                linecolor=theme_cfg["grid"],
                tickfont=dict(color=theme_cfg["text"]),
                titlefont=dict(color=theme_cfg["text"]),
            ),
            hoverlabel=dict(
                bgcolor=theme_cfg["panel"],
                bordercolor=theme_cfg["grid"],
                font=dict(color=theme_cfg["text"]),
            ),
        )
    )
    pio.templates.default = template_name
