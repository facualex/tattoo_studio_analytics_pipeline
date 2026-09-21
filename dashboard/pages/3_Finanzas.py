"""Finanzas — margen, gastos y retiros. Se activa sola cuando hay suficiente carga."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import CHART_SURFACE, GRIDLINE, INK_MUTED, INK_PRIMARY, configure_page, render_data_health_banner
from data import (
    BUSINESS_LABELS_ES,
    BUSINESS_ORDER,
    MIN_EXPENSE_ROWS_FOR_REPORTING,
    format_clp,
    load_data_health,
    load_fct_gastos,
    load_fct_retiros,
    load_fct_sesiones,
)

configure_page("Finanzas", "\U0001f4b0")
render_data_health_banner()

health = load_data_health()

if not health["expense_data_ready"]:
    st.info(
        f"Todavía no hay suficientes gastos y retiros cargados para mostrar un margen confiable "
        f"({health['gastos_rows']} gastos + {health['retiros_rows']} retiros — se necesitan "
        f"{MIN_EXPENSE_ROWS_FOR_REPORTING} en total). Esta página se activa sola apenas la hoja "
        "de Gastos/Retiros tenga suficiente carga; no hace falta pedir que se construya de nuevo."
    )
    st.stop()

sesiones = load_fct_sesiones()
gastos = load_fct_gastos()
retiros = load_fct_retiros()

# --- KPIs --------------------------------------------------------------------
total_revenue = sesiones["price_clp"].sum()
total_expenses = gastos["amount_clp"].sum()
total_withdrawals = retiros["amount_clp"].sum()
net_margin = total_revenue - total_expenses
margin_pct = (net_margin / total_revenue * 100) if total_revenue else 0

# 4 columns, not 5: st.metric truncates its value to an ellipsis based on
# measured render width (a JS width-check, not CSS — no stylesheet override
# can undo it), and CLP amounts in the millions need the room. Margen % rides
# as this metric's delta instead of taking its own column.
k1, k2, k3, k4 = st.columns(4)
k1.metric("Ingresos totales", format_clp(total_revenue))
k2.metric("Gastos totales", format_clp(total_expenses))
k3.metric("Margen neto", format_clp(net_margin), delta=f"{margin_pct:.0f}% margen")
k4.metric(
    "Retiros del dueño",
    format_clp(total_withdrawals),
    help="No se resta del margen: un retiro no es un gasto del negocio, es plata que ya era de la dueña.",
)

st.divider()

# --- Monthly revenue / expenses / margin trend --------------------------------
st.subheader("Ingresos, gastos y margen por mes")

dated_sesiones = sesiones.dropna(subset=["transaction_date"])
dated_gastos = gastos.dropna(subset=["transaction_date"])

rev_monthly = (
    dated_sesiones.assign(year_month=dated_sesiones["transaction_date"].dt.to_period("M"))
    .groupby("year_month")["price_clp"].sum()
)
exp_monthly = (
    dated_gastos.assign(year_month=dated_gastos["transaction_date"].dt.to_period("M"))
    .groupby("year_month")["amount_clp"].sum()
)

monthly = pd.DataFrame({"revenue": rev_monthly, "expenses": exp_monthly}).fillna(0).sort_index()
monthly["margin"] = monthly["revenue"] - monthly["expenses"]
monthly_x = monthly.index.to_timestamp()

loss_months = monthly[monthly["margin"] < 0]
if not loss_months.empty:
    loss_labels = ", ".join(d.strftime("%b %Y") for d in loss_months.index.to_timestamp())
    st.warning(f"⚠️ Meses con pérdida (gastos superaron a ingresos): {loss_labels}")

fig = go.Figure()
fig.add_trace(
    go.Bar(
        x=monthly_x, y=monthly["revenue"], name="Ingresos", marker_color="#2a78d6",
        hovertemplate="%{x|%b %Y}<br>Ingresos: $%{y:,.0f}<extra></extra>",
    )
)
fig.add_trace(
    go.Bar(
        x=monthly_x, y=monthly["expenses"], name="Gastos", marker_color="#e34948",
        hovertemplate="%{x|%b %Y}<br>Gastos: $%{y:,.0f}<extra></extra>",
    )
)
fig.add_trace(
    go.Scatter(
        x=monthly_x, y=monthly["margin"], name="Margen", mode="lines+markers",
        line=dict(color="#008300", width=2), marker=dict(size=6),
        hovertemplate="%{x|%b %Y}<br>Margen: $%{y:,.0f}<extra></extra>",
    )
)
fig.update_layout(
    barmode="group",
    plot_bgcolor=CHART_SURFACE,
    paper_bgcolor=CHART_SURFACE,
    font_color=INK_PRIMARY,
    margin=dict(l=10, r=10, t=10, b=10),
    height=360,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    xaxis=dict(showgrid=False, linecolor=GRIDLINE, tickfont=dict(color=INK_MUTED)),
    yaxis=dict(showgrid=True, gridcolor=GRIDLINE, tickfont=dict(color=INK_MUTED), tickprefix="$"),
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- Expense breakdown by category --------------------------------------------
st.subheader("Gastos por categoría")

categorized = gastos[gastos["category"].notna() & (gastos["category"].str.strip() != "")]
if categorized.empty:
    st.info("No hay gastos con categoría registrada.")
else:
    by_cat = (
        categorized.groupby("category", as_index=False)["amount_clp"].sum().sort_values("amount_clp", ascending=False)
    )
    TOP_N = 7
    top_cats = by_cat.head(TOP_N).copy()
    other_total = by_cat["amount_clp"].iloc[TOP_N:].sum()
    top_cats["color"] = "#e34948"
    if other_total > 0:
        top_cats = pd.concat(
            [top_cats, pd.DataFrame([{"category": "Otros", "amount_clp": other_total, "color": INK_MUTED}])]
        )
    top_cats = top_cats.sort_values("amount_clp")

    fig = go.Figure(
        data=go.Bar(
            x=top_cats["amount_clp"],
            y=top_cats["category"],
            orientation="h",
            marker_color=top_cats["color"],
            hovertemplate="%{y}: $%{x:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        plot_bgcolor=CHART_SURFACE,
        paper_bgcolor=CHART_SURFACE,
        font_color=INK_PRIMARY,
        margin=dict(l=10, r=10, t=10, b=10),
        height=320,
        xaxis=dict(showgrid=True, gridcolor=GRIDLINE, tickprefix="$", tickfont=dict(color=INK_MUTED)),
        yaxis=dict(showgrid=False),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- Profitability by business line -------------------------------------------
st.subheader("Rentabilidad por negocio")
st.caption(
    "Ingresos menos gastos registrados para cada línea de negocio. Si una línea no registra sus "
    "gastos por separado, esta comparación puede subestimar sus costos reales."
)

profit_rows = []
for biz in BUSINESS_ORDER:
    biz_revenue = sesiones[sesiones["business_line"] == biz]["price_clp"].sum()
    biz_expenses = gastos[gastos["business_line"] == biz]["amount_clp"].sum()
    profit_rows.append({"Negocio": BUSINESS_LABELS_ES[biz], "profit": biz_revenue - biz_expenses})
profit_df = pd.DataFrame(profit_rows)

fig = go.Figure(
    data=go.Bar(
        x=profit_df["profit"],
        y=profit_df["Negocio"],
        orientation="h",
        marker_color=["#008300" if p >= 0 else "#e34948" for p in profit_df["profit"]],
        hovertemplate="%{y}: $%{x:,.0f}<extra></extra>",
    )
)
fig.update_layout(
    plot_bgcolor=CHART_SURFACE,
    paper_bgcolor=CHART_SURFACE,
    font_color=INK_PRIMARY,
    margin=dict(l=10, r=10, t=10, b=10),
    height=220,
    xaxis=dict(
        showgrid=True, gridcolor=GRIDLINE, tickprefix="$", tickfont=dict(color=INK_MUTED),
        zeroline=True, zerolinecolor=INK_MUTED,
    ),
    yaxis=dict(showgrid=False),
    showlegend=False,
)
st.plotly_chart(fig, use_container_width=True)
