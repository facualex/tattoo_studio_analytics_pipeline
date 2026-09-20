"""Clientes — la vista principal: a quién contactar antes de perderlo."""

import plotly.graph_objects as go
import streamlit as st

from components import CHART_SURFACE, GRIDLINE, INK_PRIMARY, configure_page, render_data_health_banner
from data import (
    STATUS_COLORS,
    STATUS_ICONS,
    STATUS_LABELS_ES,
    VISIT_TIER_LABELS_ES,
    format_clp,
    load_dim_cliente,
)

configure_page("Clientes", "\U0001f465")
render_data_health_banner()

clientes = load_dim_cliente()

# --- KPIs ------------------------------------------------------------------
loyal = clientes[clientes["visit_tier"] == "loyal"]
loyal_at_risk = loyal[loyal["recency_status"].isin(["at_risk", "lapsed"])]

k1, k2, k3, k4 = st.columns(4)
k1.metric("Clientes totales", f"{len(clientes):,}".replace(",", "."))
k2.metric("Clientes leales (5+ visitas)", len(loyal))
k3.metric("Leales para contactar", len(loyal_at_risk), help="Leales que están en riesgo o ya no vuelven")
k4.metric("Activos (< 6 meses)", int((clientes["recency_status"] == "active").sum()))

st.divider()

# --- Actionable list: loyal clients going quiet -----------------------------
st.subheader("\U0001f3af Clientes leales para contactar")
st.caption(
    "Clientes con 5 o más visitas que no vuelven hace tiempo — ordenados por cuánto han "
    "gastado, para priorizar a quién escribirle primero."
)

if loyal_at_risk.empty:
    st.success("No hay clientes leales en riesgo en este momento.")
else:
    ranked = loyal_at_risk.sort_values("total_revenue_clp", ascending=False)
    for _, row in ranked.iterrows():
        color = STATUS_COLORS[row["recency_status"]]
        icon = STATUS_ICONS[row["recency_status"]]
        label = STATUS_LABELS_ES[row["recency_status"]]
        last_seen = row["last_transaction_date"]
        last_seen_str = last_seen.strftime("%d/%m/%Y") if last_seen is not None else "N/D"
        st.markdown(
            f"""
            <div style="border-left: 4px solid {color}; background: {CHART_SURFACE};
                        border-radius: 6px; padding: 10px 14px; margin-bottom: 8px;
                        border-top: 1px solid {GRIDLINE}; border-right: 1px solid {GRIDLINE};
                        border-bottom: 1px solid {GRIDLINE};">
                <b>{row['client_name']}</b> &nbsp; {icon} {label}
                &nbsp;·&nbsp; {row['total_visits']} visitas
                &nbsp;·&nbsp; {format_clp(row['total_revenue_clp'])} gastados
                &nbsp;·&nbsp; última visita: {last_seen_str}
                ({int(row['days_since_last_transaction'])} días)
            </div>
            """,
            unsafe_allow_html=True,
        )

st.divider()

# --- Segment overview --------------------------------------------------------
st.subheader("Todos los clientes, por segmento")
tier_order = ["new", "returning", "loyal"]
status_order = ["active", "at_risk", "lapsed"]
matrix = clientes.pivot_table(
    index="visit_tier", columns="recency_status", values="client_name", aggfunc="count", fill_value=0
).reindex(index=tier_order, columns=status_order, fill_value=0)

fig = go.Figure(
    data=go.Heatmap(
        z=matrix.values,
        x=[STATUS_LABELS_ES[s] for s in status_order],
        y=[VISIT_TIER_LABELS_ES[t] for t in tier_order],
        colorscale=[[0.0, "#cde2fb"], [0.5, "#3987e5"], [1.0, "#0d366b"]],
        text=matrix.values,
        texttemplate="%{text}",
        textfont=dict(color=INK_PRIMARY),
        hovertemplate="%{y} · %{x}: %{z} clientes<extra></extra>",
        showscale=False,
    )
)
fig.update_layout(
    plot_bgcolor=CHART_SURFACE,
    paper_bgcolor=CHART_SURFACE,
    font_color=INK_PRIMARY,
    margin=dict(l=10, r=10, t=10, b=10),
    height=260,
    xaxis=dict(showgrid=False, side="top"),
    yaxis=dict(showgrid=False),
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- Full client table ------------------------------------------------------
st.subheader("Buscar cliente")
c1, c2 = st.columns(2)
with c1:
    tier_filter = st.multiselect(
        "Categoría", options=tier_order, default=tier_order, format_func=lambda t: VISIT_TIER_LABELS_ES[t]
    )
with c2:
    status_filter = st.multiselect(
        "Estado", options=status_order, default=status_order, format_func=lambda s: STATUS_LABELS_ES[s]
    )

table = clientes[clientes["visit_tier"].isin(tier_filter) & clientes["recency_status"].isin(status_filter)].copy()
table["Categoría"] = table["visit_tier"].map(VISIT_TIER_LABELS_ES)
table["Estado"] = table["recency_status"].map(lambda s: f"{STATUS_ICONS[s]} {STATUS_LABELS_ES[s]}")
table["Ingresos totales"] = table["total_revenue_clp"].map(format_clp)
table["Ticket promedio"] = table["avg_ticket_clp"].map(format_clp)
table["Última visita"] = table["last_transaction_date"].dt.strftime("%d/%m/%Y")
table = table.sort_values("total_revenue_clp", ascending=False)

st.dataframe(
    table[
        ["client_name", "Categoría", "Estado", "total_visits", "Ingresos totales", "Ticket promedio", "Última visita"]
    ].rename(columns={"client_name": "Cliente", "total_visits": "Visitas"}),
    use_container_width=True,
    hide_index=True,
)
