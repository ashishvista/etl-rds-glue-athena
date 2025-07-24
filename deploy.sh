#!/bin/bash

# Deployment script for Data Analytics Infrastructure
set -e

echo "🚀 Starting Data Analytics Infrastructure Deployment"
echo "=================================================="

# Check if AWS CLI is configured
if ! aws sts get-caller-identity --profile test-prod > /dev/null 2>&1; then
    echo "❌ AWS SSO profile 'test-prod' not configured or not logged in"
    echo "Please run: aws sso login --profile test-prod"
    exit 1
fi

echo "✅ AWS credentials verified"

# Check if Terraform is installed
if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform is not installed"
    echo "Please install Terraform: https://www.terraform.io/downloads.html"
    exit 1
fi

echo "✅ Terraform found"

# Check if Python dependencies are installed
if ! python3 -c "import psycopg2, boto3, pandas" 2>/dev/null; then
    echo "📦 Installing Python dependencies..."
    pip3 install -r requirements.txt
fi

echo "✅ Python dependencies verified"

# Initialize Terraform
echo "🔧 Initializing Terraform..."
terraform init

# Validate Terraform configuration
echo "🔍 Validating Terraform configuration..."
terraform validate

# Plan the deployment
echo "📋 Creating Terraform plan..."
terraform plan -out=tfplan

# Ask for confirmation
read -p "🤔 Do you want to apply this plan? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Deployment cancelled"
    exit 1
fi

# Apply the infrastructure
echo "🏗️  Deploying infrastructure..."
terraform apply tfplan

echo "✅ Infrastructure deployed successfully!"

# Get outputs
echo "📊 Getting deployment outputs..."
RDS_ENDPOINT=$(terraform output -raw rds_endpoint)
S3_BUCKET=$(terraform output -raw s3_bucket_name)
CUSTOMERS_ETL_JOB=$(terraform output -raw customers_etl_job_name)
ORDERS_ETL_JOB=$(terraform output -raw orders_etl_job_name)
ATHENA_WORKGROUP=$(terraform output -raw athena_workgroup_name)

echo ""
echo "🎉 Deployment Complete!"
echo "======================"
echo "RDS Endpoint: $RDS_ENDPOINT"
echo "S3 Data Lake Bucket: $S3_BUCKET"
echo "Customers ETL Job: $CUSTOMERS_ETL_JOB"
echo "Orders ETL Job: $ORDERS_ETL_JOB"
echo "Athena Workgroup: $ATHENA_WORKGROUP"
echo ""

# Ask if user wants to load sample data
read -p "📥 Do you want to load sample data into the database? (yes/no): " load_data
if [ "$load_data" == "yes" ]; then
    echo "📥 Loading sample data..."
    python3 load_data.py "$RDS_ENDPOINT" "analytics_db" "analytics_user" "ChangeMe123!"
    
    echo "🚀 Starting complete ETL pipeline (jobs + crawler)..."
    python3 run_glue_jobs.py run-pipeline
    
    echo "✅ Complete pipeline executed. Schema should now be available in Glue Catalog."
fi

echo ""
echo "🎯 Next Steps:"
echo "1. Open AWS Athena Console"
echo "2. Select workgroup: $ATHENA_WORKGROUP" 
echo "3. Check available tables: SHOW TABLES IN data_analytics_database;"
echo "4. Run the pre-created named queries for data analysis"
echo "5. Check S3 bucket: $S3_BUCKET for the data lake files"
echo ""
echo "📚 For more information, see README.md"
echo "🔄 For incremental testing, see INCREMENTAL_ETL.md"
