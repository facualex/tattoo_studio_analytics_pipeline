# Tattoo Studio Analytics Pipeline

An end-to-end data pipeline that turns a small business's scattered records (Google Sheets + photographed receipts) into a financial analytics dashboard — built to solve a real operational problem for a real business owner running three creative micro-businesses (tattoo art, makeup, and fine art).

> **The problem:** the business owner tracked 900+ tattoo sessions, expenses, and withdrawals across multiple spreadsheets with no way to answer basic questions like "what's my real margin this month?" or "which clients haven't come back in a while?"
>
> **The solution:** a pipeline that ingests data from Google Sheets, models it into a clean dimensional structure, and serves it through an interactive dashboard — with zero manual spreadsheet wrangling required.

---



## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Google Sheets  │────▶│   AWS S3 (raw)    │────▶│       dbt        │
│  (source of truth)│     │  Medallion: raw/  │     │ staging → marts  │
└─────────────────┘     │  staging/marts    │     └────────┬────────┘
                          └──────────────────┘              │
                                                               ▼
        ┌───────────────────────────────────────────┐  ┌──────────────────┐
        │   Apache Airflow (Dockerized, local)        │  │   AWS Athena      │
        │   orchestrates the daily pipeline run        │  │  (query engine)   │
        └───────────────────────────────────────────┘  └────────┬────────┘
                                                                   │
                                                                   ▼
                                                            ┌──────────────┐
                                                            │  Streamlit    │
                                                            │  Dashboard    │
                                                            │  (deployed)   │
                                                            └──────────────┘
```

*Diagram placeholder — will be replaced with a proper architecture image.*

This is the target architecture. Today, dbt and the dashboard both read directly from local Parquet/DuckDB rather than S3/Athena — a deliberate local-dev shortcut (see [Status](#status)) that gets swapped for the real path once the S3 bucket and Athena workgroup are provisioned.

---



## Why this stack


| Layer          | Tool                           | Why                                                                                                                                                    |
| -------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Ingestion      | `gspread`                      | Pulls structured data directly from the business's live Google Sheets                                                                                  |
| Storage        | AWS S3                         | Medallion architecture (raw → staging → marts), industry-standard pattern                                                                              |
| Transformation | dbt                            | Version-controlled SQL, tested business logic, not spreadsheet formulas                                                                                |
| Orchestration  | Apache Airflow (Docker, local) | Demonstrates DAG design without paying for 24/7 managed infrastructure (see [cost notes](#cost-management))                                            |
| Query engine   | AWS Athena                     | Serverless, pay-per-query — the right fit for a dataset this size                                                                                      |
| Visualization  | Streamlit                      | Full control over UI logic (conditional client-risk alerts, contact buttons) that BI tools like Looker Studio can't express without manual workarounds |


---



## Key design decisions

- **Airflow runs locally in Docker, not on AWS MWAA.** A managed Airflow environment costs roughly $350–400/month running 24/7 — not justifiable for this data volume. The orchestration logic is identical; only the hosting differs. This was a deliberate cost-engineering decision, not a shortcut.
- **Athena over Redshift/a traditional warehouse.** With a dataset in the hundreds of MB, a serverless pay-per-query model is both cheaper and architecturally more honest than provisioning always-on compute.
- **Parquet + partitioning by year/month.** Even at this data volume, the project follows the same columnar storage and partition-pruning practices used in production-scale Athena deployments — see [docs/cost_analysis.md](docs/cost_analysis.md).
- **AWS Budget with cost alerts configured at 50%/80% thresholds**, plus an Athena workgroup byte-scan limit as a technical safety net — see [docs/cost_analysis.md](docs/cost_analysis.md) for the full reasoning.
- **The dashboard never shows a number it can't back up.** ~37% of tattoo sessions are recorded at $0 (missing price input, a smaller share genuine trades) — every revenue/ticket metric explicitly excludes them instead of silently averaging them in. The margin view stays dormant behind a data-completeness check (`gastos + retiros ≥ 20` rows) and explains what's missing instead of rendering a misleadingly healthy margin off of 3 real expense rows. Both the check and the caveats live in one place so they can't drift out of sync with what's actually on screen.
- **Revenue isn't silently dropped for a messy client name.** A handful of sales had a blank or clearly-wrong client field (sheet template rows, e.g. a calendar month sitting in the name column); those get kept under `client_name = 'unknown'` so the revenue still counts, but excluded from client-level loyalty/churn segmentation so they don't get miscounted as a single high-value repeat client.

---



## What the dashboard answers

Four pages, running locally today (from `dashboard/`: `source .venv/bin/activate && streamlit run app.py`); online deploy with authentication is still pending.

| Page | Answers | Status |
| --- | --- | --- |
| **Resumen** | Real revenue, ticket trends, and seasonality — which months are reliably strong or weak, across 3+ years of sessions | ✅ live |
| **Clientes** | Who are the loyal clients (5+ visits) at risk of churning, ranked by how much they've spent; client lifetime value by loyalty tier; new-vs-returning ratio per month | ✅ live |
| **Negocios** | How tattoo/art/makeup compare on revenue and ticket size; revenue by style | ✅ live |
| **Finanzas** | Net margin, loss-month flags, expenses by category, profitability per business line | 🟡 built, dormant until expense data is complete enough to report on honestly (see [Key design decisions](#key-design-decisions)) |

Two questions from the original scope aren't answered anywhere yet, because there's no real data behind either one: **acquisition-channel performance** (the field exists in the sheet but is ~100% blank) and **Meta Ads ROAS** (no ad-spend source is extracted at all). Rather than ship an empty chart, both are parked until a real data source exists.

*Dashboard screenshots and live demo link — coming once deployed.*

---



## Project structure

```
tattoo-studio-analytics-pipeline/
├── ingest/                 # Sheets extraction
├── airflow/                # DAG definitions (Dockerized, local orchestration)
├── dbt/                    # staging → intermediate → marts models
├── infra/                  # Terraform: S3, IAM, Athena workgroup, budgets
├── dashboard/               # Streamlit app
├── monitoring/              # Data quality checks
└── docs/                   # Architecture, cost analysis, data dictionary
```

---



## Cost management

This project deliberately optimizes for near-zero operating cost while still demonstrating production-grade architecture decisions. Full breakdown in [docs/cost_analysis.md](docs/cost_analysis.md), including:

- Estimated monthly AWS spend (under $5/month for this data volume)
- Why MWAA was ruled out
- Athena query optimization practices applied (Parquet, partitioning, compression)
- AWS Budget Actions and Athena workgroup limits as cost safety nets

---



## Status

🚧 **In progress.** This README will be updated with screenshots, a live dashboard link, and a recorded walkthrough as each module is completed.


| Module                          | Status                                                                          |
| -------------------------------- | -------------------------------------------------------------------------------- |
| Google Sheets extraction         | ✅                                                                                |
| Terraform (S3, IAM, Athena, Budget) | 🟡 written, not yet applied — no AWS resources exist yet                      |
| S3 raw layer                     | 🔲 blocked on the Terraform apply above                                         |
| dbt models (staging → intermediate → marts) | ✅ all layers built and tested, but reading local Parquet/DuckDB, not S3/Athena — see [Architecture](#architecture) |
| Data quality fixes               | 🟡 known issues (sheet template rows, a few unattributed sales) fixed at the model layer; formal `monitoring/` checks not started |
| Airflow DAG                      | 🔲                                                                                |
| Streamlit dashboard              | 🟡 4 pages built and running locally; online deploy + auth pending              |
| Deployment (S3 serving layer + Streamlit Cloud) | 🔲                                                                    |


---



## Author

Built by [Facundo] — Data Engineer transitioning from legacy ETL tools toward cloud-native data engineering. This project was built as a real solution for a real client, and doubles as a portfolio piece demonstrating the dbt → Airflow → AWS stack end-to-end.