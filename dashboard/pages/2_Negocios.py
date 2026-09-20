"""Negocios — cómo se compara cada línea (tatuajes, arte, maquillaje)."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import CHART_SURFACE, GRIDLINE, INK_MUTED, INK_PRIMARY, configure_page, render_data_health_banner
from data import BUSINESS_COLORS, BUSINESS_LABELS_ES, BUSINESS_ORDER, format_clp, load_fct_sesiones

configure_page("Negocios", "\U0001f3a8")
render_data_health_banner()

sesiones = load_fct_sesiones()
dated = sesiones.dropna(subset=["transaction_date"])
total_revenue = sesiones["price_clp"].sum()

# --- Comparison table --------------------------------------------------------
st.subheader("Comparación por línea de negocio")

summary_rows = []
for biz in BUSINESS_ORDER:
    biz_rows = sesiones[sesiones["business_line"] == biz]
    paid = biz_rows[biz_rows["price_clp"] > 0]
    revenue = biz_rows["price_clp"].sum()
    summary_rows.append(
        {
            "Negocio": BUSINESS_LABELS_ES[biz],
            "Ingresos": revenue,
            "% del total": round((revenue / total_revenue * 100) if total_revenue else 0, 1),
            "Sesiones": len(biz_rows),
            "Ticket promedio": paid["price_clp"].mean() if len(paid) else None,
        }
    )
summary = pd.DataFrame(summary_rows)

display_summary = summary.copy()
display_summary["Ingresos"] = display_summary["Ingresos"].map(format_clp)
display_summary["% del total"] = display_summary["% del total"].map(lambda v: f"{v:.1f}%")
display_summary["Ticket promedio"] = display_summary["Ticket promedio"].map(format_clp)

st.dataframe(display_summary, use_container_width=True, hide_index=True)

st.divider()

# --- Revenue share (bar, not pie — 3 categories compare cleanly on one axis) -
st.subheader("Participación en los ingresos")
fig = go.Figure()
fig.add_trace(
    go.Bar(
        x=summary["Ingresos"],
        y=summary["Negocio"],
        orientation="h",
        marker_color=[BUSINESS_COLORS[b] for b in BUSINESS_ORDER],
        hovertemplate="%{y}: $%{x:,.0f}<extra></extra>",
    )
)
fig.update_layout(
    plot_bgcolor=CHART_SURFACE,
    paper_bgcolor=CHART_SURFACE,
    font_color=INK_PRIMARY,
    margin=dict(l=10, r=10, t=10, b=10),
    height=220,
    xaxis=dict(showgrid=True, gridcolor=GRIDLINE, tickprefix="$", tickfont=dict(color=INK_MUTED)),
    yaxis=dict(showgrid=False),
    showlegend=False,
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- Revenue trend by business line ------------------------------------------
st.subheader("Ingresos por mes, por negocio")
if dated.empty:
    st.info("No hay sesiones con fecha disponibles.")
else:
    trend_src = dated.assign(year_month=dated["transaction_date"].dt.to_period("M").dt.to_timestamp())
    trend = trend_src.groupby(["year_month", "business_line"], as_index=False)["price_clp"].sum()

    fig = go.Figure()
    for biz in BUSINESS_ORDER:
        biz_trend = trend[trend["business_line"] == biz]
        fig.add_trace(
            go.Scatter(
                x=biz_trend["year_month"],
                y=biz_trend["price_clp"],
                mode="lines",
                name=BUSINESS_LABELS_ES[biz],
                line=dict(color=BUSINESS_COLORS[biz], width=2),
                hovertemplate="%{x|%b %Y}<br>$%{y:,.0f}<extra>" + BUSINESS_LABELS_ES[biz] + "</extra>",
            )
        )
    fig.update_layout(
        plot_bgcolor=CHART_SURFACE,
        paper_bgcolor=CHART_SURFACE,
        font_color=INK_PRIMARY,
        margin=dict(l=10, r=10, t=10, b=10),
        height=340,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis=dict(showgrid=False, linecolor=GRIDLINE, tickfont=dict(color=INK_MUTED)),
        yaxis=dict(showgrid=True, gridcolor=GRIDLINE, tickfont=dict(color=INK_MUTED), tickprefix="$"),
    )
    st.plotly_chart(fig, use_container_width=True)
