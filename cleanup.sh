#!/bin/bash

# Cleanup script for Data Analytics Infrastructure
set -e

echo "🧹 Data Analytics Infrastructure Cleanup"
echo "========================================"

# Check if AWS CLI is configured
if ! aws sts get-caller-identity --profile test-prod > /dev/null 2>&1; then
    echo "❌ AWS SSO profile 'test-prod' not configured or not logged in"
    echo "Please run: aws sso login --profile test-prod"
    exit 1
fi

echo "✅ AWS credentials verified"

# Ask for confirmation
echo "⚠️  WARNING: This will destroy all infrastructure including:"
echo "   - RDS PostgreSQL database and all data"
echo "   - S3 buckets and all stored data"
echo "   - Lambda functions"
echo "   - Glue catalog and tables"
echo "   - Athena workgroup and named queries"
echo ""
read -p "🤔 Are you sure you want to destroy everything? (type 'yes' to confirm): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Cleanup cancelled"
    exit 1
fi

# Get S3 bucket names before destroying to empty them
echo "📊 Getting S3 bucket information..."
if [ -f terraform.tfstate ]; then
    DATA_LAKE_BUCKET=$(terraform output -raw s3_bucket_name 2>/dev/null || echo "")
    
    if [ ! -z "$DATA_LAKE_BUCKET" ]; then
        echo "🗑️  Emptying S3 bucket: $DATA_LAKE_BUCKET"
        aws s3 rm s3://$DATA_LAKE_BUCKET --recursive --profile test-prod || true
        
        # Also check for athena results bucket
        ATHENA_BUCKET="${DATA_LAKE_BUCKET/data-lake/athena-results}"
        echo "🗑️  Emptying S3 bucket: $ATHENA_BUCKET"
        aws s3 rm s3://$ATHENA_BUCKET --recursive --profile test-prod || true
    fi
fi

# Destroy the infrastructure
echo "💥 Destroying Terraform infrastructure..."
terraform destroy -auto-approve

echo "🧹 Cleaning up local files..."
rm -f terraform.tfstate*
rm -f tfplan
rm -f .terraform.lock.hcl
rm -rf .terraform/

echo ""
echo "✅ Cleanup completed successfully!"
echo "All AWS resources have been destroyed."
