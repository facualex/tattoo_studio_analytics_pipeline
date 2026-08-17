output "bucket_name" {
  description = "Name of the created S3 bucket"
  value       = aws_s3_bucket.data_lake.id
}

output "bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.data_lake.arn
}

output "athena_results_path" {
  description = "S3 path to use as the Athena Workgroup output location"
  value       = "s3://${aws_s3_bucket.data_lake.id}/athena-results/"
}

output "iam_user_name" {
  description = "Name of the IAM user created for local Airflow"
  value       = aws_iam_user.airflow_local.name
}

output "aws_access_key_id" {
  description = "Access Key ID to configure in .env (AWS_ACCESS_KEY_ID)"
  value       = aws_iam_access_key.airflow_local.id
}

output "aws_secret_access_key" {
  description = "Secret Access Key to configure in .env (AWS_SECRET_ACCESS_KEY). Only shown once."
  value       = aws_iam_access_key.airflow_local.secret
  sensitive   = true
}

output "serving_path" {
  description = "S3 path of the serving layer consumed by the Streamlit dashboard"
  value       = "s3://${aws_s3_bucket.data_lake.id}/serving/"
}

output "streamlit_iam_user_name" {
  description = "Name of the read-only IAM user created for the Streamlit dashboard"
  value       = aws_iam_user.streamlit_serving.name
}

output "streamlit_aws_access_key_id" {
  description = "Access Key ID to configure as a secret in Streamlit Community Cloud"
  value       = aws_iam_access_key.streamlit_serving.id
}

output "streamlit_aws_secret_access_key" {
  description = "Secret Access Key to configure as a secret in Streamlit Community Cloud. Only shown once."
  value       = aws_iam_access_key.streamlit_serving.secret
  sensitive   = true
}

output "athena_workgroup_name" {
  description = "Name of the Athena workgroup to use when running queries (enforces the per-query bytes-scanned cutoff)"
  value       = aws_athena_workgroup.main.name
}
