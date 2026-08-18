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
- **Parquet + partitioning by year/month.** Even at this data volume, the project follows the same columnar storage and partition-pruning practices used in production-scale Athena deployments — see `[docs/cost_analysis.md](docs/cost_analysis.md)`.
- **AWS Budget with cost alerts configured at 50%/80% thresholds**, plus an Athena workgroup byte-scan limit as a technical safety net — see `[docs/cost_analysis.md](docs/cost_analysis.md)` for the full reasoning.

---



## What the dashboard answers

- What's the real monthly revenue, expense, and net margin — across all three businesses?
- Who are the loyal clients (5+ visits), and who's at risk of churning?
- Which acquisition channel brings in clients that actually convert and stay?
- Is a given Meta Ads campaign profitable (ROAS), or burning money?
- What's the seasonality pattern across years — which months are reliably strong or weak?

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

This project deliberately optimizes for near-zero operating cost while still demonstrating production-grade architecture decisions. Full breakdown in `[docs/cost_analysis.md](docs/cost_analysis.md)`, including:

- Estimated monthly AWS spend (under $5/month for this data volume)
- Why MWAA was ruled out
- Athena query optimization practices applied (Parquet, partitioning, compression)
- AWS Budget Actions and Athena workgroup limits as cost safety nets

---



## Status

🚧 **In progress.** This README will be updated with screenshots, a live dashboard link, and a recorded walkthrough as each module is completed.


| Module                     | Status |
| -------------------------- | ------ |
| Google Sheets extraction   | ✅      |
| S3 raw layer               | 🔲     |
| dbt models (staging/marts) | 🔲     |
| Airflow DAG                | 🔲     |
| Streamlit dashboard        | 🔲     |
| Terraform infra            | 🔲     |


---



## Author

Built by [Facundo] — Data Engineer transitioning from legacy ETL tools toward cloud-native data engineering. This project was built as a real solution for a real client, and doubles as a portfolio piece demonstrating the dbt → Airflow → AWS stack end-to-end.