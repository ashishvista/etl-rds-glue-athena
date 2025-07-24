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

# 7. Run Glue ETL pipeline
python3 run_glue_jobs.py run-all
```

## Managing ETL Jobs

### Running ETL Jobs
```bash
# List all available Glue jobs
python3 run_glue_jobs.py list

# Run all ETL jobs
python3 run_glue_jobs.py run-all

# Run specific job
python3 run_glue_jobs.py run data-analytics-customers-etl

# Monitor running job
python3 run_glue_jobs.py monitor <job_name> <run_id>
```

## Architecture Benefits

### Glue Spark ETL Advantages:
- **Scalable**: Handles datasets from MBs to TBs
- **Serverless**: No infrastructure management
- **Cost-Effective**: Pay per job execution
- **Fault Tolerant**: Automatic retries and error handling
- **Incremental**: Job bookmarking for delta processing