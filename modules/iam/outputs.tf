output "lambda_role_arn" {
  description = "Lambda execution role ARN"
  value       = aws_iam_role.lambda_role.arn
}

output "glue_role_arn" {
  description = "Glue service role ARN"
  value       = aws_iam_role.glue_role.arn
}
