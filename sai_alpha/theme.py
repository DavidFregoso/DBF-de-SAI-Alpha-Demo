from __future__ import annotations

from typing import Any

import plotly.io as pio
import streamlit as st


def get_theme_config(theme_name: str) -> dict[str, Any]:
    normalized = (theme_name or "Claro").strip().lower()
    if normalized == "oscuro":
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


def apply_global_css(theme_cfg: dict[str, Any]) -> None:
    bg = theme_cfg["bg"]
    panel = theme_cfg["panel"]
    text = theme_cfg["text"]
    muted = theme_cfg["muted"]
    accent = theme_cfg["accent"]
    grid = theme_cfg["grid"]
    is_dark = theme_cfg["name"] == "Oscuro"
    st.markdown(
        f"""
        <style>
            :root {{
                color-scheme: { "dark" if is_dark else "light" };
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
                background-color: {bg};
                color: {text};
            }}

            [data-testid="stSidebar"] {{
                background-color: {panel};
                min-width: 360px;
                width: 360px;
            }}
            [data-testid="stSidebar"] > div {{
                min-width: 360px;
                width: 360px;
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
                color: {text};
            }}

            .app-header {{
                font-weight: 700;
                font-size: 1.4rem;
                color: {accent};
                margin-bottom: 0.25rem;
            }}
            .app-subtitle {{
                color: {muted};
                margin-top: 0;
            }}
            .top-header {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1rem;
                padding: 0.75rem 1rem;
                border-radius: 12px;
                background: {panel};
                border: 1px solid {grid};
                margin-bottom: 1.5rem;
            }}
            .top-header-title {{
                font-weight: 700;
                font-size: 1.3rem;
                color: {accent};
            }}
            .top-header-sub {{
                color: {muted};
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
                background: {bg};
                border: 1px solid {grid};
                border-radius: 999px;
                padding: 0.35rem 0.75rem;
                font-size: 0.8rem;
                color: {text};
                box-shadow: 0 1px 2px rgba(0,0,0,0.04);
            }}
            .refresh-box {{
                display: flex;
                flex-direction: column;
                align-items: flex-end;
                gap: 0.35rem;
            }}
            .refresh-label {{
                color: {muted};
                font-size: 0.8rem;
            }}
            [data-testid="stMetricValue"] {{
                color: {accent};
            }}
            [data-testid="stMetricDelta"] {{
                color: {accent};
            }}
            .section-title {{
                border-left: 4px solid {accent};
                padding-left: 0.6rem;
                font-weight: 600;
                font-size: 1.1rem;
                color: {text};
            }}
            .sidebar-title {{
                font-weight: 700;
                font-size: 1.05rem;
                color: {accent};
                margin-bottom: 0.1rem;
            }}
            .sidebar-subtitle {{
                color: {muted};
                font-size: 0.85rem;
                margin-top: 0;
            }}
            .sidebar-theme {{
                color: {text};
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
                background: {panel};
                border: 1px solid {grid};
                color: {text};
            }}
            [data-testid="stDataFrame"] thead tr th {{
                background: {bg};
                color: {text};
                border-bottom: 1px solid {grid};
            }}
            [data-testid="stDataFrame"] tbody tr td {{
                color: {text};
                border-bottom: 1px solid {grid};
            }}
            [data-testid="stDataFrame"] tbody tr:hover {{
                background: { "#1f2937" if is_dark else "rgba(0,0,0,0.04)" };
            }}

            .stSelectbox > div > div,
            .stMultiSelect > div > div,
            .stTextInput > div > div,
            .stDateInput > div > div {{
                background-color: {bg};
                color: {text};
                border-color: {grid};
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
