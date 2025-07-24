variable "project_name" {
  description = "Project name"
  type        = string
}

variable "s3_bucket_name" {
  description = "S3 bucket name for query results"
  type        = string
}

variable "glue_database_name" {
  description = "Glue database name"
  type        = string
}
