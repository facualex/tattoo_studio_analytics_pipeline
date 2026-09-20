# Cost Analysis

This project is unpaid portfolio work (no client billing attached), so the
guiding principle is: **near-zero cost during development, and structural
caps that make it hard to accidentally spend real money even while
iterating.**

---

## Why the cost surface is small by design

There is no always-on compute anywhere in this stack:

| What would normally cost money | What this project does instead |
| --- | --- |
| A managed Airflow environment (AWS MWAA, ~$350–400/month running 24/7) | Airflow runs locally in Docker — only costs your laptop's electricity |
| An always-on data warehouse (Redshift, etc.) | AWS Athena — serverless, pay only per query scanned |
| A always-on app host for the dashboard | Streamlit Community Cloud — free tier |

The only two things that can generate an AWS bill at all are S3 storage and
Athena query scans, and both are bounded on purpose.

## S3

- Dataset is currently a few hundred KB of Parquet (870 tattoo sessions +
  a handful of art/makeup/expense rows) — storage cost is a fraction of a
  cent per month at S3 Standard rates (~$0.023/GB/month).
- `aws_s3_bucket_lifecycle_configuration` expires `raw/`, `staging/`, and
  `marts/` objects after 3 days, and `athena-results/` after 5 days, so
  storage cost can't quietly accumulate across dev runs — old partitions
  self-delete.
- Versioning is deliberately off, which avoids paying for duplicate
  historical copies of every object.
- No cross-region replication, no Glacier tiering — none of that is needed
  at this volume and would only add complexity.

**Realistic S3 cost: well under $0.10/month.**

## Athena

This is the only "pay per action" resource, so it's the one to watch
during active development (i.e. while iterating on dbt models and running
manual queries).

- `aws_athena_workgroup.main` sets `bytes_scanned_cutoff_per_query` to 5 GB
  by default, and `enforce_workgroup_configuration = true` makes that cap
  mandatory — a query can't opt out of it, even by accident.
- At $5/TB scanned, a single query capped at 5 GB costs at most **$0.025**.
- Parquet + year/month partitioning means well-written queries scan far
  less than the cap in practice — the 5 GB number is a worst-case ceiling,
  not the expected cost per query.
- Back-of-envelope: even a sloppy dev session running 50 uncapped-feeling
  queries in a day costs at most ~$1.25. You would need hundreds of
  worst-case queries in a month to approach the default $15 budget.

**Realistic Athena cost during active dbt development: a few cents to low
dollars per month, hard-capped from going higher per query.**

## Budgets (safety net, not prevention)

`aws_budgets_budget.monthly_cost` currently sends an email when spend
crosses:

- 80% of `monthly_budget_usd` (ACTUAL spend)
- 100% of `monthly_budget_usd` (FORECASTED spend)

Two caveats worth knowing:

1. **AWS Budgets data can lag several hours**, so this is a same-day
   tripwire, not a real-time one. A CloudWatch billing alarm (metric
   `EstimatedCharges`) is free and updates faster, and is worth adding as
   a second, quicker tripwire if you want tighter feedback while actively
   developing.
2. **Budgets only notify — they don't stop anything** unless paired with
   AWS Budgets Actions (e.g. auto-attaching a deny-all IAM policy), which
   isn't configured here. Given the hard per-query Athena cap and the
   absence of always-on compute, the blast radius of "nobody sees the
   email in time" is already small — but it's not literally zero.
3. The README currently describes 50%/80% alert thresholds; `main.tf`
   currently implements 80%/100%. Worth reconciling — either update the
   README, or add a 50% (ACTUAL) notification block back into
   `aws_budgets_budget.monthly_cost` for earlier visibility during the
   dev period specifically.

`monthly_budget_usd` defaults to $15 (`infra/variables.tf`). For a dev
phase with no client billing behind it, a lower ceiling (e.g. $5) via
`infra/terraform.tfvars` would trigger the alert email sooner without
changing any infrastructure logic.

## IAM

No cost. Both IAM users (`airflow_local`, `streamlit_serving`) are
scoped to least privilege on this one bucket — `airflow_local` gets
read/write on the whole bucket, `streamlit_serving` is read-only and
scoped to `serving/*` only, so a leaked Streamlit secret can't touch
raw/staging/marts or run up an Athena bill.

## Practical recommendation for the development phase

You don't need AWS running at all to build most of this pipeline:

- **dbt models can be developed entirely offline** against the local
  Parquet files in `ingest/data/tmp/` using the `dbt-duckdb` adapter —
  zero AWS cost, faster iteration than waiting on Athena round-trips.
  Only switch the dbt target to Athena once staging/marts models are
  stable and you actually want to validate them against the real
  workgroup.
- Run `terraform apply` only when you're ready to test the S3/Athena
  legs specifically, and `terraform destroy` between extended breaks if
  you want to be extra conservative — though at this cost profile
  (no always-on resources), leaving it applied is not itself a spend
  risk, just a "why pay for anything I'm not actively using" preference.
- Keep an eye on Cost Explorer filtered by the `Project` tag
  (`tattoo-studio-analytics`) applied to every resource in `main.tf`, to
  see exactly what this project — and nothing else in the account —
  is costing.

## Estimated monthly spend

| Phase | Estimated cost |
| --- | --- |
| Local-only dev (dbt-duckdb, no `terraform apply` yet) | $0 |
| Active dev with infra applied, moderate Athena querying | $0.05–$2 |
| Steady state (daily Airflow DAG run, dashboard live) | Under $5/month |
