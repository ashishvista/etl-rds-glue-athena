output "workgroup_name" {
  description = "Athena workgroup name"
  value       = aws_athena_workgroup.main.name
}

output "named_queries" {
  description = "List of named query names"
  value = [
    aws_athena_named_query.customer_orders_summary.name,
    aws_athena_named_query.monthly_sales_trend.name,
    aws_athena_named_query.top_products.name
  ]
}
