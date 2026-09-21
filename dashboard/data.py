"""
Data access layer for the dashboard.

Reads directly from the local dbt DuckDB dev database — the same local-dev
shortcut dbt itself uses (see dbt/models/staging/stg_tatuajes.sql and
dbt_project.yml's raw_data_dir comment). Once the Airflow DAG uploads the
marts to the S3 serving/ prefix (see infra/main.tf's serving_prefix), this
should swap to reading Parquet from there instead of the local DuckDB file,
so the dashboard doesn't depend on a dbt run having happened on this machine.
"""

from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

DUCKDB_PATH = Path(__file__).resolve().parent.parent / "dbt" / "dev.duckdb"

CALENDAR_MONTHS_ES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

BUSINESS_LABELS_ES = {"tattoo": "Tatuajes", "art": "Arte", "makeup": "Maquillaje"}

# Fixed categorical order (slots 1-3: blue/orange/aqua) — never re-sorted by
# value, so a business line keeps its color across every chart in the app.
BUSINESS_ORDER = ["tattoo", "art", "makeup"]
BUSINESS_COLORS = {"tattoo": "#2a78d6", "art": "#eb6834", "makeup": "#1baf7a"}

STATUS_COLORS = {"active": "#0ca30c", "at_risk": "#fab219", "lapsed": "#d03b3b"}
STATUS_LABELS_ES = {"active": "Activo", "at_risk": "En riesgo", "lapsed": "Perdido"}
STATUS_ICONS = {"active": "\U0001f7e2", "at_risk": "\U0001f7e0", "lapsed": "\U0001f534"}

VISIT_TIER_LABELS_ES = {"new": "Nuevo", "returning": "Recurrente", "loyal": "Leal"}

# Below this many combined gastos+retiros rows, expense data is too sparse to
# report on honestly (see the data-health banner and the Finanzas page — both
# read this same flag so there's one place that decides "is it ready", not
# two thresholds that can drift apart).
MIN_EXPENSE_ROWS_FOR_REPORTING = 20


def _connect() -> duckdb.DuckDBPyConnection:
    if not DUCKDB_PATH.exists():
        st.error(
            f"No se encontró la base de datos en `{DUCKDB_PATH}`. "
            "Corré `dbt build` en dbt/ antes de levantar el dashboard."
        )
        st.stop()
    return duckdb.connect(str(DUCKDB_PATH), read_only=True)


@st.cache_data(ttl=300)
def load_fct_sesiones() -> pd.DataFrame:
    with _connect() as con:
        return con.sql("select * from main.fct_sesiones").df()


@st.cache_data(ttl=300)
def load_dim_cliente() -> pd.DataFrame:
    with _connect() as con:
        return con.sql("select * from main.dim_cliente").df()


@st.cache_data(ttl=300)
def load_fct_gastos() -> pd.DataFrame:
    with _connect() as con:
        return con.sql("select * from main.fct_gastos").df()


@st.cache_data(ttl=300)
def load_fct_retiros() -> pd.DataFrame:
    with _connect() as con:
        return con.sql("select * from main.fct_retiros").df()


@st.cache_data(ttl=300)
def load_data_health() -> dict:
    sesiones = load_fct_sesiones()
    gastos = load_fct_gastos()
    retiros = load_fct_retiros()

    total_rows = len(sesiones)
    zero_price_rows = int((sesiones["price_clp"] == 0).sum())
    null_date_rows = int(sesiones["transaction_date"].isna().sum())

    expense_rows = len(gastos) + len(retiros)

    return {
        "as_of_date": sesiones["transaction_date"].max(),
        "total_sessions": total_rows,
        "zero_price_rows": zero_price_rows,
        "pct_zero_price": (zero_price_rows / total_rows * 100) if total_rows else 0,
        "null_date_rows": null_date_rows,
        "gastos_rows": len(gastos),
        "retiros_rows": len(retiros),
        "expense_data_ready": expense_rows >= MIN_EXPENSE_ROWS_FOR_REPORTING,
    }


def format_clp(value: float | int) -> str:
    """Chilean peso formatting: no decimals, '.' as the thousands separator."""
    if pd.isna(value):
        return "N/D"
    return f"${value:,.0f}".replace(",", ".")
