############################################
# S3 — Main bucket with Medallion layers
############################################

resource "aws_s3_bucket" "data_lake" {
  bucket = var.bucket_name

  tags = {
    Project   = var.project_name
    ManagedBy = "terraform"
  }
}

# Full public access block. This bucket is only accessed via
# authenticated Athena/IAM, it must never be public.
resource "aws_s3_bucket_public_access_block" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Versioning off on purpose: this is a low-volume project and enabling
# versioning adds duplicated storage cost with no real benefit here.
resource "aws_s3_bucket_versioning" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  versioning_configuration {
    status = "Disabled"
  }
}

# Default server-side encryption (SSE-S3, no extra KMS cost)
resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Medallion "folders". S3 doesn't have real folders, they're just key
# prefixes, but creating these empty objects helps visualize the structure
# in the console and acts as an anchor for the DAG's paths.
resource "aws_s3_object" "raw_prefix" {
  bucket  = aws_s3_bucket.data_lake.id
  key     = "raw/"
  content = ""
}

resource "aws_s3_object" "staging_prefix" {
  bucket  = aws_s3_bucket.data_lake.id
  key     = "staging/"
  content = ""
}

resource "aws_s3_object" "marts_prefix" {
  bucket  = aws_s3_bucket.data_lake.id
  key     = "marts/"
  content = ""
}

# Separate prefix for Athena query results (required: Athena needs an
# output bucket/prefix configured on the workgroup).
resource "aws_s3_object" "athena_results_prefix" {
  bucket  = aws_s3_bucket.data_lake.id
  key     = "athena-results/"
  content = ""
}

# Serving layer for the Streamlit dashboard: the last task of the Airflow
# DAG uploads the Parquet with the Gold layer aggregates (dbt) here, and
# only updates last_updated.txt once that upload succeeded. Streamlit never
# queries Athena live, it only reads from this prefix.
resource "aws_s3_object" "serving_prefix" {
  bucket  = aws_s3_bucket.data_lake.id
  key     = "serving/"
  content = ""
}

# Lifecycle rules to keep storage cost bounded over time. The DAG runs
# daily and partitions raw/staging/marts by execution date, and we only
# need the last ~3 daily runs around — so every data layer expires after
# 3 days. athena-results/ is unrelated to run partitions (it's disposable
# query output) and gets its own 5-day window.
resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    id     = "expire-athena-results"
    status = "Enabled"
    filter {
      prefix = "athena-results/"
    }
    expiration {
      days = 5
    }
  }

  rule {
    id     = "expire-raw"
    status = "Enabled"
    filter {
      prefix = "raw/"
    }
    expiration {
      days = 3
    }
  }

  rule {
    id     = "expire-staging"
    status = "Enabled"
    filter {
      prefix = "staging/"
    }
    expiration {
      days = 3
    }
  }

  rule {
    id     = "expire-marts"
    status = "Enabled"
    filter {
      prefix = "marts/"
    }
    expiration {
      days = 3
    }
  }
}

############################################
# Athena — Workgroup with a per-query cost cap
############################################

# enforce_workgroup_configuration = true makes the cutoff and output
# location mandatory for every query run under this workgroup, overriding
# whatever a client tries to set — otherwise the cutoff is only a default
# that callers could bypass.
resource "aws_athena_workgroup" "main" {
  name = "${var.project_name}-workgroup"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
    bytes_scanned_cutoff_per_query     = var.athena_bytes_scanned_cutoff_per_query

    result_configuration {
      output_location = "s3://${aws_s3_bucket.data_lake.id}/athena-results/"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }

  tags = {
    Project = var.project_name
  }
}

############################################
# Budgets — account-wide cost guardrail
############################################

# Account-wide (not tag-filtered) so it works with zero extra setup: tag-based
# budget filters require activating cost allocation tags in Billing
# preferences first, which isn't exposed as a Terraform resource. Email
# subscribers don't require confirmation, unlike SNS.
resource "aws_budgets_budget" "monthly_cost" {
  name         = "${var.project_name}-monthly-budget"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.budget_alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.budget_alert_email]
  }
}

############################################
# IAM — User + Policy with minimal permissions
############################################

# Programmatic user so Airflow (running locally) can read/write to the
# bucket. No console access, only API access via access keys.
resource "aws_iam_user" "airflow_local" {
  name = "${var.project_name}-airflow-local"

  tags = {
    Project = var.project_name
  }
}

data "aws_iam_policy_document" "s3_access" {
  # Allows listing the bucket (needed for operations like `aws s3 ls`,
  # and so boto3/Athena can resolve paths), but scoped to this bucket only.
  statement {
    sid     = "ListBucket"
    effect  = "Allow"
    actions = ["s3:ListBucket"]
    resources = [
      aws_s3_bucket.data_lake.arn
    ]
  }

  # Allows reading, writing and deleting objects, but ONLY within this
  # specific bucket — no access to any other bucket in the account.
  # Already covers serving/* (including s3:PutObject there for the last
  # DAG task that uploads the Parquet and last_updated.txt) — no separate
  # statement is needed since this one already applies to the whole bucket.
  statement {
    sid    = "ReadWriteObjects"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [
      "${aws_s3_bucket.data_lake.arn}/*"
    ]
  }
}

resource "aws_iam_policy" "s3_access" {
  name        = "${var.project_name}-s3-access"
  description = "Minimal read/write access to the project's data lake bucket"
  policy      = data.aws_iam_policy_document.s3_access.json
}

resource "aws_iam_user_policy_attachment" "airflow_local_s3" {
  user       = aws_iam_user.airflow_local.name
  policy_arn = aws_iam_policy.s3_access.arn
}

# Programmatic access key. The secret key is only shown ONCE in the
# `terraform apply` output (and stays in the state file, see the README
# note about protecting terraform.tfstate — it must never be pushed to git).
resource "aws_iam_access_key" "airflow_local" {
  user = aws_iam_user.airflow_local.name
}

############################################
# IAM — User + Policy for Streamlit (serving layer)
############################################

# Dedicated user for the Streamlit Community Cloud dashboard (deployed
# outside AWS, hence access keys instead of an IAM role). No console
# access, and no permissions at all over raw/staging/marts/athena-results:
# it can only read the serving/ prefix.
resource "aws_iam_user" "streamlit_serving" {
  name = "${var.project_name}-streamlit-serving"

  tags = {
    Project = var.project_name
  }
}

data "aws_iam_policy_document" "streamlit_serving_read" {
  # ListBucket scoped to the serving/ prefix via the s3:prefix condition,
  # so this user can't list the rest of the bucket.
  statement {
    sid     = "ListServingPrefix"
    effect  = "Allow"
    actions = ["s3:ListBucket"]
    resources = [
      aws_s3_bucket.data_lake.arn
    ]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["serving/*"]
    }
  }

  # Read-only, scoped to serving/* only.
  statement {
    sid     = "ReadServingObjects"
    effect  = "Allow"
    actions = ["s3:GetObject"]
    resources = [
      "${aws_s3_bucket.data_lake.arn}/serving/*"
    ]
  }
}

resource "aws_iam_policy" "streamlit_serving_read" {
  name        = "${var.project_name}-streamlit-serving-read"
  description = "Read-only access to the serving/ prefix of the data lake, for the Streamlit dashboard"
  policy      = data.aws_iam_policy_document.streamlit_serving_read.json
}

resource "aws_iam_user_policy_attachment" "streamlit_serving_read" {
  user       = aws_iam_user.streamlit_serving.name
  policy_arn = aws_iam_policy.streamlit_serving_read.arn
}

# Access key to configure as secrets in Streamlit Community Cloud
# (st.secrets), never hardcoded in the dashboard code.
resource "aws_iam_access_key" "streamlit_serving" {
  user = aws_iam_user.streamlit_serving.name
}
