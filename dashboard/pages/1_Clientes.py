"""Clientes — la vista principal: a quién contactar antes de perderlo."""

import plotly.graph_objects as go
import streamlit as st

from components import CHART_SURFACE, GRIDLINE, INK_MUTED, INK_PRIMARY, configure_page, render_data_health_banner
from data import (
    STATUS_COLORS,
    STATUS_ICONS,
    STATUS_LABELS_ES,
    VISIT_TIER_LABELS_ES,
    format_clp,
    load_dim_cliente,
    load_fct_sesiones,
)

configure_page("Clientes", "\U0001f465")
render_data_health_banner()

clientes = load_dim_cliente()

TIER_ORDER = ["new", "returning", "loyal"]
STATUS_ORDER = ["active", "at_risk", "lapsed"]
# Ordinal ramp (one hue, light -> dark) — loyalty is ordered, not categorical,
# so color intensity itself carries "more loyal" the way it does elsewhere
# for magnitude. Steps 250/450/650 from the dataviz skill's sequential blue.
TIER_ORDINAL_COLORS = {"new": "#86b6ef", "returning": "#2a78d6", "loyal": "#104281"}

# --- KPIs ------------------------------------------------------------------
loyal = clientes[clientes["visit_tier"] == "loyal"]
loyal_at_risk = loyal[loyal["recency_status"].isin(["at_risk", "lapsed"])]

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Clientes totales", f"{len(clientes):,}".replace(",", "."))
k2.metric("Clientes leales (5+ visitas)", len(loyal))
k3.metric("Leales para contactar", len(loyal_at_risk), help="Leales que están en riesgo o ya no vuelven")
k4.metric("Activos (< 6 meses)", int((clientes["recency_status"] == "active").sum()))
k5.metric(
    "CLV promedio",
    format_clp(clientes["total_revenue_clp"].mean()),
    help="Ingresos totales históricos, promediados entre todos los clientes reales.",
)

st.divider()

# --- CLV by loyalty tier: why the retention list below matters -------------
st.subheader("Valor de por vida (CLV), por categoría de cliente")
st.caption("Cuánto deja en promedio un cliente según cuántas veces ha vuelto — el argumento para no dejar ir a un leal.")

clv_by_tier = (
    clientes.groupby("visit_tier")["total_revenue_clp"].mean().reindex(TIER_ORDER).fillna(0)
)
# Labels live INSIDE the bar, not "outside": outside text on the longest bar
# in a use_container_width chart gets clipped by the SVG's own boundary
# regardless of figure margin/axis range (a Plotly+responsive-width quirk,
# not something margin tuning fixes) — inside text can't overflow.
# Text color flips per bar so it stays readable against the light "Nuevo"
# bar vs. the dark "Leal" one.
inside_text_colors = {"new": INK_PRIMARY, "returning": "#ffffff", "loyal": "#ffffff"}
fig = go.Figure(
    data=go.Bar(
        x=[clv_by_tier[t] for t in TIER_ORDER],
        y=[VISIT_TIER_LABELS_ES[t] for t in TIER_ORDER],
        orientation="h",
        marker_color=[TIER_ORDINAL_COLORS[t] for t in TIER_ORDER],
        text=[format_clp(clv_by_tier[t]) for t in TIER_ORDER],
        textposition="inside",
        insidetextanchor="end",
        textfont=dict(color=[inside_text_colors[t] for t in TIER_ORDER]),
        hovertemplate="%{y}: %{text}<extra></extra>",
    )
)
fig.update_layout(
    plot_bgcolor=CHART_SURFACE,
    paper_bgcolor=CHART_SURFACE,
    font_color=INK_PRIMARY,
    margin=dict(l=10, r=10, t=10, b=10),
    height=200,
    xaxis=dict(showgrid=True, gridcolor=GRIDLINE, tickprefix="$", tickfont=dict(color=INK_MUTED)),
    yaxis=dict(showgrid=False),
    showlegend=False,
)
st.plotly_chart(fig, use_container_width=True)

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

# --- New vs returning clients per month -------------------------------------
st.subheader("Nuevos vs. recurrentes, por mes")
st.caption(
    "Un cliente cuenta como “nuevo” el mes de su primera visita, y como “recurrente” "
    "cualquier mes posterior en que vuelva. Muestra si el negocio crece con caras nuevas o vive de las conocidas."
)

sesiones = load_fct_sesiones()
dated_named = sesiones.dropna(subset=["transaction_date"])
dated_named = dated_named[dated_named["client_name"] != "unknown"]

visits = dated_named.assign(year_month=dated_named["transaction_date"].dt.to_period("M"))
visits = visits.drop_duplicates(["client_name", "year_month"])[["client_name", "year_month"]]

first_visit = clientes[["client_name", "first_transaction_date"]].dropna().copy()
first_visit["first_year_month"] = first_visit["first_transaction_date"].dt.to_period("M")

joined = visits.merge(first_visit[["client_name", "first_year_month"]], on="client_name", how="inner")
joined["segment"] = joined.apply(
    lambda r: "new" if r["year_month"] == r["first_year_month"] else "returning", axis=1
)

if joined.empty:
    st.info("No hay suficientes datos con fecha para calcular esta vista.")
else:
    monthly = joined.groupby(["year_month", "segment"]).size().unstack(fill_value=0)
    for seg in ["new", "returning"]:
        if seg not in monthly.columns:
            monthly[seg] = 0
    monthly = monthly.sort_index()
    monthly_x = monthly.index.to_timestamp()

    overall_new = int(joined["segment"].eq("new").sum())
    overall_returning = int(joined["segment"].eq("returning").sum())
    overall_total = overall_new + overall_returning
    st.caption(
        f"Histórico completo: {overall_new / overall_total:.0%} nuevos "
        f"· {overall_returning / overall_total:.0%} recurrentes ({overall_total} visitas-cliente-mes)."
    )

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=monthly_x, y=monthly["new"], name="Nuevos",
            marker_color="#86b6ef",
            hovertemplate="%{x|%b %Y}<br>Nuevos: %{y}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=monthly_x, y=monthly["returning"], name="Recurrentes",
            marker_color="#104281",
            hovertemplate="%{x|%b %Y}<br>Recurrentes: %{y}<extra></extra>",
        )
    )
    fig.update_layout(
        barmode="stack",
        plot_bgcolor=CHART_SURFACE,
        paper_bgcolor=CHART_SURFACE,
        font_color=INK_PRIMARY,
        margin=dict(l=10, r=10, t=10, b=10),
        height=320,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis=dict(showgrid=False, linecolor=GRIDLINE, tickfont=dict(color=INK_MUTED)),
        yaxis=dict(showgrid=True, gridcolor=GRIDLINE, tickfont=dict(color=INK_MUTED)),
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- Segment overview --------------------------------------------------------
st.subheader("Todos los clientes, por segmento")
matrix = clientes.pivot_table(
    index="visit_tier", columns="recency_status", values="client_name", aggfunc="count", fill_value=0
).reindex(index=TIER_ORDER, columns=STATUS_ORDER, fill_value=0)

fig = go.Figure(
    data=go.Heatmap(
        z=matrix.values,
        x=[STATUS_LABELS_ES[s] for s in STATUS_ORDER],
        y=[VISIT_TIER_LABELS_ES[t] for t in TIER_ORDER],
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
        "Categoría", options=TIER_ORDER, default=TIER_ORDER, format_func=lambda t: VISIT_TIER_LABELS_ES[t]
    )
with c2:
    status_filter = st.multiselect(
        "Estado", options=STATUS_ORDER, default=STATUS_ORDER, format_func=lambda s: STATUS_LABELS_ES[s]
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
