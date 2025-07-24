output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = module.rds.rds_endpoint
}

output "s3_bucket_name" {
  description = "S3 data lake bucket name"
  value       = module.s3.data_lake_bucket_name
}

output "glue_database_name" {
  description = "Glue database name"
  value       = module.glue.glue_database_name
}

output "athena_workgroup_name" {
  description = "Athena workgroup name"
  value       = module.athena.workgroup_name
}

output "customers_etl_job_name" {
  description = "Customers Glue ETL job name"
  value       = module.glue.customers_etl_job_name
}

output "orders_etl_job_name" {
  description = "Orders Glue ETL job name"
  value       = module.glue.orders_etl_job_name
}

output "etl_trigger_name" {
  description = "ETL trigger name"
  value       = module.glue.etl_trigger_name
}
