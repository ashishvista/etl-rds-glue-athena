output "data_lake_bucket_name" {
  description = "Data lake S3 bucket name"
  value       = aws_s3_bucket.data_lake.id
}

output "data_lake_bucket_arn" {
  description = "Data lake S3 bucket ARN"
  value       = aws_s3_bucket.data_lake.arn
}

output "athena_results_bucket_name" {
  description = "Athena results S3 bucket name"
  value       = aws_s3_bucket.athena_results.id
}

output "athena_results_bucket_arn" {
  description = "Athena results S3 bucket ARN"
  value       = aws_s3_bucket.athena_results.arn
}
