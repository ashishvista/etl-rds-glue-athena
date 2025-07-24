variable "project_name" {
  description = "Project name"
  type        = string
}

variable "s3_bucket_arn" {
  description = "S3 bucket ARN for data lake"
  type        = string
}

variable "rds_endpoint" {
  description = "RDS endpoint"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs"
  type        = list(string)
}
