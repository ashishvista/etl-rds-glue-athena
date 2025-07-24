# Data Analytics Infrastructure

This project creates a complete data analytics infrastructure on AWS using Terraform, including:

- PostgreSQL RDS database
- S3 data lake
- AWS Glue Spark ETL jobs (scalable for large datasets)
- AWS Glue data catalog
- Amazon Athena for querying

## Prerequisites

1. AWS CLI configured with SSO profile "test-prod"
2. Terraform installed (>= 1.0)
3. Python 3.9+ with pip

## Setup Instructions

### 1. Configure AWS SSO

```bash
aws configure sso --profile test-prod
aws sso login --profile test-prod
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Plan the deployment
terraform plan

# Apply the infrastructure
terraform apply
```

### 4. Load Sample Data

After the infrastructure is deployed, get the RDS endpoint and load sample data:

```bash
# Get RDS endpoint from Terraform output
RDS_ENDPOINT=$(terraform output -raw rds_endpoint)

# Load sample data into PostgreSQL
python3 load_data.py $RDS_ENDPOINT analytics_db analytics_user ChangeMe123!
```

### 5. Run ETL Pipeline

Trigger the Glue ETL jobs to extract data from RDS and load into S3:

```bash
# Run complete pipeline (ETL + crawler)
python3 run_glue_jobs.py run-pipeline

# Or run just ETL jobs
python3 run_glue_jobs.py run-all

# Or run individual components
python3 run_glue_jobs.py run data-analytics-customers-etl
python3 run_glue_jobs.py run data-analytics-orders-etl
python3 run_glue_jobs.py run-crawler data-analytics-crawler

# List all available jobs and crawlers
python3 run_glue_jobs.py list
```

### 6. Query Data with Athena

1. Open AWS Athena console
2. Select the workgroup: `data-analytics-workgroup`
3. Use the pre-created named queries:
   - `customer_orders_summary` - Customer spending analysis
   - `monthly_sales_trend` - Monthly sales trends
   - `top_products` - Top products by revenue

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │───▶│  Glue Spark     │───▶│   S3 Data Lake  │
│   RDS Instance  │    │   ETL Jobs      │    │   (Parquet)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Athena      │◀───│   AWS Glue      │◀───│  Glue Crawler   │
│   Queries       │    │  Data Catalog   │    │ (Schema Detect) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Why Glue Instead of Lambda?

- **Scalability**: Glue can handle large datasets (TBs) without timeout limitations
- **Spark Power**: Built-in Apache Spark for distributed processing
- **Job Bookmarking**: Automatic incremental processing
- **Cost Effective**: Pay only for resources used during job execution
- **Auto Scaling**: Automatically scales based on data volume

## Modules

- **RDS**: PostgreSQL database with security groups and subnet groups
- **S3**: Data lake bucket with encryption and versioning
- **IAM**: Roles and policies for Glue services with RDS connection
- **Glue**: Spark ETL jobs, data catalog, crawler, and scheduled triggers
- **Athena**: Workgroup and named queries for data analysis

## Sample Queries

### Customer Orders Summary
```sql
SELECT 
    c.customer_id,
    c.name,
    c.email,
    COUNT(o.order_id) as total_orders,
    SUM(o.quantity * o.price) as total_spent,
    AVG(o.quantity * o.price) as avg_order_value
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name, c.email
ORDER BY total_spent DESC;
```

### Monthly Sales Trend
```sql
SELECT 
    EXTRACT(YEAR FROM order_date) as year,
    EXTRACT(MONTH FROM order_date) as month,
    COUNT(order_id) as total_orders,
    SUM(quantity * price) as total_revenue
FROM orders
GROUP BY EXTRACT(YEAR FROM order_date), EXTRACT(MONTH FROM order_date)
ORDER BY year, month;
```

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

## Cost Optimization

- RDS instance uses `db.t3.micro` (free tier eligible)
- Lambda function has timeout set to 5 minutes
- S3 buckets use standard storage class
- Glue crawler runs daily at 2 AM

## Security Features

- VPC with private subnets for RDS
- Security groups with minimal required access
- S3 buckets with encryption and public access blocked
- IAM roles with least privilege principle

## Monitoring

- CloudWatch logs for Lambda function
- Athena query metrics in CloudWatch
- S3 access logging (optional)

## Troubleshooting

### Lambda Function Issues
```bash
# Check Lambda logs
aws logs describe-log-groups --profile test-prod --log-group-name-prefix "/aws/lambda/data-analytics"

# Get recent logs
aws logs filter-log-events --profile test-prod --log-group-name "/aws/lambda/data-analytics-etl-lambda"
```

### RDS Connection Issues
- Ensure Lambda is in the same VPC as RDS
- Check security group rules
- Verify database credentials

### Athena Query Issues
- Run Glue crawler to update schema
- Check S3 data format (should be Parquet)
- Verify table definitions in Glue catalog
