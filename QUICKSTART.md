# Quick Start Guide

## Prerequisites Check

Before starting, ensure you have:

1. **AWS CLI with SSO configured:**
   ```bash
   aws configure sso --profile test-prod
   aws sso login --profile test-prod
   ```

2. **Terraform installed:**
   ```bash
   # On macOS with Homebrew
   brew install terraform
   
   # Verify installation
   terraform --version
   ```

3. **Python 3.9+ with pip:**
   ```bash
   python3 --version
   pip3 --version
   ```

## Deployment Steps

### Option 1: Automated Deployment (Recommended)

```bash
# Clone or navigate to the project directory
cd /Users/ashish_kumar/data-analytics

# Run the automated deployment script
./deploy.sh
```

The script will:
- Verify prerequisites
- Install Python dependencies
- Initialize and validate Terraform
- Deploy the infrastructure
- Optionally load sample data
- Run the Glue ETL pipeline

### Option 2: Manual Deployment

```bash
# 1. Install Python dependencies
pip3 install -r requirements.txt

# 2. Initialize Terraform
terraform init

# 3. Validate configuration
terraform validate

# 4. Create deployment plan
terraform plan -out=tfplan

# 5. Apply the infrastructure
terraform apply tfplan

# 6. Load sample data (optional)
# Get RDS endpoint from output
RDS_ENDPOINT=$(terraform output -raw rds_endpoint)
python3 load_data.py "$RDS_ENDPOINT" "analytics_db" "analytics_user" "ChangeMe123!"

# 7. Run complete ETL pipeline (includes crawler)
python3 run_glue_jobs.py run-pipeline
```

## Managing ETL Jobs

### Running ETL Jobs & Crawler
```bash
# List all available Glue jobs and crawlers
python3 run_glue_jobs.py list

# Run complete pipeline (ETL + crawler for schema discovery)
python3 run_glue_jobs.py run-pipeline

# Run just ETL jobs
python3 run_glue_jobs.py run-all

# Run specific job
python3 run_glue_jobs.py run data-analytics-customers-etl

# Run crawler manually
python3 run_glue_jobs.py run-crawler data-analytics-crawler

# Monitor running job
python3 run_glue_jobs.py monitor <job_name> <run_id>
```

## Schema Discovery Process

The infrastructure uses a **crawler-only approach** for schema management:

1. **ETL Jobs** → Process data and write Parquet files to S3
2. **Glue Crawler** → Automatically discovers schema from Parquet metadata
3. **Glue Catalog** → Creates/updates table definitions
4. **Athena** → Queries using discovered schema

### Benefits:
- **Automatic Schema Evolution**: Handles new columns automatically
- **No Schema Conflicts**: Single source of truth from actual data
- **Partition Discovery**: Automatically finds year/month/day partitions
- **Data Type Accuracy**: Infers optimal types from Parquet files

## Architecture Benefits

### Glue Spark ETL Advantages:
- **Scalable**: Handles datasets from MBs to TBs
- **Serverless**: No infrastructure management
- **Cost-Effective**: Pay per job execution
- **Fault Tolerant**: Automatic retries and error handling
- **Incremental**: Job bookmarking for delta processing
- **Schema Flexible**: Crawler adapts to data changes