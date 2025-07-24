output "glue_database_name" {
  description = "Glue database name"
  value       = aws_glue_catalog_database.main.name
}

output "glue_crawler_name" {
  description = "Glue crawler name"
  value       = aws_glue_crawler.data_lake_crawler.name
}

output "customers_etl_job_name" {
  description = "Customers ETL job name"
  value       = aws_glue_job.customers_etl.name
}

output "orders_etl_job_name" {
  description = "Orders ETL job name"
  value       = aws_glue_job.orders_etl.name
}

output "etl_trigger_name" {
  description = "ETL trigger name"
  value       = aws_glue_trigger.etl_trigger.name
}
