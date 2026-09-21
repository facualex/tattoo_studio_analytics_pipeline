"""Shared page chrome: page config, light theme tokens, and the data-health banner."""

import streamlit as st

from data import MIN_EXPENSE_ROWS_FOR_REPORTING, STATUS_COLORS, STATUS_ICONS, STATUS_LABELS_ES, load_data_health

# Chart chrome tokens (light mode) — see the dataviz skill's palette.md.
PAGE_PLANE = "#f9f9f7"
CHART_SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"


def configure_page(title: str, icon: str) -> None:
    st.set_page_config(page_title=f"{title} · Estudio", page_icon=icon, layout="wide")
    st.markdown(
        f"""
        <style>
            .stApp {{ background-color: {PAGE_PLANE}; }}
            [data-testid="stMetric"] {{
                background-color: {CHART_SURFACE};
                border: 1px solid {GRIDLINE};
                border-radius: 8px;
                padding: 12px 16px;
            }}
            [data-testid="stMetricLabel"] {{ color: {INK_SECONDARY}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title(f"{icon} {title}")


def render_data_health_banner() -> None:
    """Persistent, always-visible trust signal — not buried in a footnote."""
    health = load_data_health()
    as_of = health["as_of_date"]
    as_of_str = as_of.strftime("%d/%m/%Y") if as_of is not None else "N/D"

    warnings = []
    if health["pct_zero_price"] > 0:
        warnings.append(
            f"{health['pct_zero_price']:.0f}% de las sesiones "
            f"({health['zero_price_rows']} de {health['total_sessions']}) no tienen "
            "precio registrado (falta de carga o trueques) y se excluyen del ticket promedio."
        )
    if health["null_date_rows"] > 0:
        warnings.append(
            f"{health['null_date_rows']} sesiones con ingreso real no tienen fecha registrada "
            "y no aparecen en las vistas por período."
        )
    if not health["expense_data_ready"]:
        warnings.append(
            f"Solo hay {health['gastos_rows']} gastos y {health['retiros_rows']} retiros "
            f"cargados (se necesitan {MIN_EXPENSE_ROWS_FOR_REPORTING} en total) — la página "
            "Finanzas todavía no muestra el margen: hoy sería un número engañosamente alto."
        )

    with st.container(border=True):
        st.caption(f"\U0001f4c5 Datos al {as_of_str}")
        for w in warnings:
            st.caption(f"⚠️ {w}")


def status_badge_html(status: str) -> str:
    color = STATUS_COLORS[status]
    icon = STATUS_ICONS[status]
    label = STATUS_LABELS_ES[status]
    return (
        f'<span style="border-left: 3px solid {color}; padding-left: 6px;">'
        f"{icon} {label}</span>"
    )
