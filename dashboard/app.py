"""Resumen — ingresos, ticket promedio y estacionalidad."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import CHART_SURFACE, GRIDLINE, INK_MUTED, INK_PRIMARY, configure_page, render_data_health_banner
from data import BUSINESS_LABELS_ES, BUSINESS_ORDER, format_clp, load_fct_sesiones

configure_page("Resumen", "\U0001f4ca")
render_data_health_banner()

sesiones = load_fct_sesiones()

# --- Filters -----------------------------------------------------------
col_f1, col_f2 = st.columns([2, 3])
with col_f1:
    selected_lines = st.multiselect(
        "Negocio",
        options=BUSINESS_ORDER,
        default=BUSINESS_ORDER,
        format_func=lambda k: BUSINESS_LABELS_ES[k],
    )
with col_f2:
    min_date = sesiones["transaction_date"].min()
    max_date = sesiones["transaction_date"].max()
    date_range = st.date_input("Rango de fechas", value=(min_date, max_date), min_value=min_date, max_value=max_date)

filtered = sesiones[sesiones["business_line"].isin(selected_lines)]
if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    filtered = filtered[
        filtered["transaction_date"].isna()
        | filtered["transaction_date"].between(start, end)
    ]

paid = filtered[filtered["price_clp"] > 0]

# --- KPIs ----------------------------------------------------------------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Ingresos totales", format_clp(filtered["price_clp"].sum()))
k2.metric("Sesiones totales", f"{len(filtered):,}".replace(",", "."))
k3.metric("Sesiones pagadas", f"{len(paid):,}".replace(",", "."))
k4.metric("Ticket promedio", format_clp(paid["price_clp"].mean()) if len(paid) else "N/D")

st.divider()

dated = filtered.dropna(subset=["transaction_date"])

# --- Monthly revenue trend ------------------------------------------------
st.subheader("Ingresos por mes")
if dated.empty:
    st.info("No hay sesiones con fecha para el filtro seleccionado.")
else:
    monthly = (
        dated.assign(year_month=dated["transaction_date"].dt.to_period("M").dt.to_timestamp())
        .groupby("year_month", as_index=False)["price_clp"]
        .sum()
    )
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=monthly["year_month"],
            y=monthly["price_clp"],
            mode="lines",
            line=dict(color="#2a78d6", width=2, shape="spline"),
            fill="tozeroy",
            fillcolor="rgba(42, 120, 214, 0.08)",
            hovertemplate="%{x|%b %Y}<br>$%{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        plot_bgcolor=CHART_SURFACE,
        paper_bgcolor=CHART_SURFACE,
        font_color=INK_PRIMARY,
        margin=dict(l=10, r=10, t=10, b=10),
        height=340,
        xaxis=dict(showgrid=False, linecolor=GRIDLINE, tickfont=dict(color=INK_MUTED)),
        yaxis=dict(showgrid=True, gridcolor=GRIDLINE, tickfont=dict(color=INK_MUTED), tickprefix="$"),
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Seasonality heatmap ---------------------------------------------------
st.subheader("Estacionalidad: ¿qué meses son fuertes o débiles?")
st.caption("Suma de ingresos por mes calendario en cada año — permite ver si un patrón se repite.")
if dated.empty:
    st.info("No hay sesiones con fecha para el filtro seleccionado.")
else:
    heat_src = dated.assign(year=dated["transaction_date"].dt.year, month=dated["transaction_date"].dt.month)
    heat = heat_src.groupby(["year", "month"], as_index=False)["price_clp"].sum()
    pivot = heat.pivot(index="year", columns="month", values="price_clp").reindex(columns=range(1, 13))
    month_labels = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=month_labels,
            y=[str(y) for y in pivot.index],
            colorscale=[
                [0.0, "#cde2fb"], [0.2, "#9ec5f4"], [0.4, "#6da7ec"],
                [0.6, "#3987e5"], [0.8, "#256abf"], [1.0, "#0d366b"],
            ],
            hovertemplate="%{y} · %{x}<br>$%{z:,.0f}<extra></extra>",
            colorbar=dict(tickprefix="$", outlinewidth=0),
        )
    )
    fig.update_layout(
        plot_bgcolor=CHART_SURFACE,
        paper_bgcolor=CHART_SURFACE,
        font_color=INK_PRIMARY,
        margin=dict(l=10, r=10, t=10, b=10),
        height=280,
        xaxis=dict(showgrid=False, side="top"),
        yaxis=dict(showgrid=False, autorange="reversed"),
    )
    st.plotly_chart(fig, use_container_width=True)
