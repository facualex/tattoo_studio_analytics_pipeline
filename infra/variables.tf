variable "aws_region" {
  description = "AWS region where all the infrastructure is deployed"
  type        = string
  default     = "us-east-1" # us-east-1 is usually the cheapest for S3 + Athena
}

variable "project_name" {
  description = "Project name, used as a prefix to name resources"
  type        = string
  default     = "tattoo-studio-analytics"
}

variable "bucket_name" {
  description = <<-EOT
    S3 bucket name. Must be unique GLOBALLY across all of AWS (not just
    within your account), so you'll probably need a random suffix or
    your own identifier. E.g.: tattoo-studio-analytics-facu-2026
  EOT
  type        = string
}

variable "athena_bytes_scanned_cutoff_per_query" {
  description = "Hard cap on bytes scanned per Athena query, to bound worst-case query cost ($5/TB scanned). Default is 5 GB (~$0.025/query worst case)."
  type        = number
  default     = 5368709120
}

variable "monthly_budget_usd" {
  description = "Total monthly AWS cost threshold (account-wide) that triggers budget alert emails"
  type        = number
  default     = 15
}

variable "budget_alert_email" {
  description = "Email address that receives AWS Budgets alerts when spend crosses the configured thresholds"
  type        = string
}
