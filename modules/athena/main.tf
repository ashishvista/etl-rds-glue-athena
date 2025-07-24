# Athena Workgroup
resource "aws_athena_workgroup" "main" {
  name = "${var.project_name}-workgroup"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${var.s3_bucket_name}/athena-results/"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }

  tags = {
    Name = "${var.project_name}-workgroup"
  }
}

# Athena Named Queries for common analytics
resource "aws_athena_named_query" "customer_orders_summary" {
  name      = "customer_orders_summary"
  database  = var.glue_database_name
  workgroup = aws_athena_workgroup.main.name

  query = <<EOF
SELECT 
    c.customer_id,
    c.name,
    c.email,
    COUNT(o.order_id) as total_orders,
    SUM(o.quantity * o.price) as total_spent,
    AVG(o.quantity * o.price) as avg_order_value,
    MIN(o.order_date) as first_order_date,
    MAX(o.order_date) as last_order_date
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name, c.email
ORDER BY total_spent DESC;
EOF

  description = "Customer orders summary with spending analysis"
}

resource "aws_athena_named_query" "monthly_sales_trend" {
  name      = "monthly_sales_trend"
  database  = var.glue_database_name
  workgroup = aws_athena_workgroup.main.name

  query = <<EOF
SELECT 
    EXTRACT(YEAR FROM order_date) as year,
    EXTRACT(MONTH FROM order_date) as month,
    COUNT(order_id) as total_orders,
    SUM(quantity * price) as total_revenue,
    AVG(quantity * price) as avg_order_value,
    COUNT(DISTINCT customer_id) as unique_customers
FROM orders
GROUP BY EXTRACT(YEAR FROM order_date), EXTRACT(MONTH FROM order_date)
ORDER BY year, month;
EOF

  description = "Monthly sales trend analysis"
}

resource "aws_athena_named_query" "top_products" {
  name      = "top_products"
  database  = var.glue_database_name
  workgroup = aws_athena_workgroup.main.name

  query = <<EOF
SELECT 
    product_name,
    COUNT(order_id) as order_count,
    SUM(quantity) as total_quantity_sold,
    SUM(quantity * price) as total_revenue,
    AVG(price) as avg_price
FROM orders
GROUP BY product_name
ORDER BY total_revenue DESC
LIMIT 20;
EOF

  description = "Top 20 products by revenue"
}
