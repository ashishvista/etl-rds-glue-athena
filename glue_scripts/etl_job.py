import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql import functions as F
from datetime import datetime, timedelta
import boto3

# Get job parameters
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'source_table',
    'target_path',
    'database_name',
    'connection_name'
])

# Initialize Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

def get_last_processed_timestamp(s3_bucket, table_name):
    """Get the last processed timestamp from S3 metadata or job bookmark"""
    
    try:
        # Try to get from S3 metadata file first
        s3_client = boto3.client('s3')
        metadata_key = f"etl-metadata/{table_name}/last_processed_timestamp.txt"
        
        response = s3_client.get_object(Bucket=s3_bucket, Key=metadata_key)
        last_timestamp = response['Body'].read().decode('utf-8').strip()
        print(f"📅 Found last processed timestamp for {table_name}: {last_timestamp}")
        return last_timestamp
        
    except Exception as e:
        print(f"ℹ️  No previous timestamp found for {table_name}, processing all data: {str(e)}")
        # For first run, process data from 30 days ago to avoid full table scan
        default_timestamp = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        return default_timestamp

def save_last_processed_timestamp(s3_bucket, table_name, timestamp):
    """Save the last processed timestamp to S3 for next run"""
    
    try:
        s3_client = boto3.client('s3')
        metadata_key = f"etl-metadata/{table_name}/last_processed_timestamp.txt"
        
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=metadata_key,
            Body=timestamp,
            ContentType='text/plain'
        )
        print(f"💾 Saved last processed timestamp for {table_name}: {timestamp}")
        
    except Exception as e:
        print(f"⚠️  Failed to save timestamp for {table_name}: {str(e)}")

def extract_from_rds_incremental(table_name, connection_name, last_timestamp):
    """Extract only new/updated data from RDS PostgreSQL based on timestamp"""
    
    print(f"🔍 Extracting incremental data for {table_name} since {last_timestamp}")
    
    # For first run or when no timestamp metadata exists, get all data
    # Check if this looks like a default timestamp (30 days ago)
    default_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    if last_timestamp.startswith(default_date):
        print(f"🚀 First run detected for {table_name}, extracting all data")
        # For first run, use simple table reference
        dbtable = f"public.{table_name}"
    else:
        # Build incremental query based on table
        if table_name == "customers":
            # For customers, check both created_at and updated_at
            dbtable = f"""(SELECT * FROM public.{table_name} 
             WHERE created_at > '{last_timestamp}' 
                OR updated_at > '{last_timestamp}') as incremental_data"""
        elif table_name == "orders":
            # For orders, check both order_date and updated_at
            dbtable = f"""(SELECT * FROM public.{table_name} 
             WHERE order_date >= '{last_timestamp[:10]}'
                OR updated_at > '{last_timestamp}') as incremental_data"""
        else:
            # Default: use updated_at if available, otherwise all data
            dbtable = f"""(SELECT * FROM public.{table_name} 
             WHERE updated_at > '{last_timestamp}' 
                OR created_at > '{last_timestamp}') as incremental_data"""
    
    print(f"📝 Using dbtable: {dbtable}")
    
    # Read from PostgreSQL using incremental query
    dynamic_frame = glueContext.create_dynamic_frame.from_options(
        connection_type="postgresql",
        connection_options={
            "useConnectionProperties": "true",
            "dbtable": dbtable,
            "connectionName": connection_name,
        },
        transformation_ctx=f"extract_incremental_{table_name}"
    )
    
    record_count = dynamic_frame.count()
    print(f"📊 Found {record_count} incremental records for {table_name}")
    
    return dynamic_frame

def transform_data(dynamic_frame, table_name):
    """Apply transformations to the data"""
    
    # Convert to Spark DataFrame for transformations
    df = dynamic_frame.toDF()
    
    if df.count() == 0:
        print(f"ℹ️  No data to transform for {table_name}")
        return dynamic_frame
    
    # Add processing metadata
    current_time = datetime.now()
    df = df.withColumn("etl_processed_at", F.lit(current_time))
    df = df.withColumn("etl_job_run_id", F.lit(args['JOB_NAME'] + "_" + current_time.strftime("%Y%m%d_%H%M%S")))
    
    # Table-specific transformations
    if table_name == "customers":
        # Add customer lifecycle stage based on creation date
        df = df.withColumn(
            "customer_lifecycle_days",
            F.datediff(F.current_date(), F.col("created_at"))
        )
        
        df = df.withColumn(
            "customer_segment",
            F.when(F.col("customer_lifecycle_days") < 30, "New")
            .when(F.col("customer_lifecycle_days") < 365, "Active")
            .otherwise("Mature")
        )
    
    elif table_name == "orders":
        # Add order value categories and date partitions
        df = df.withColumn(
            "order_value",
            F.col("quantity") * F.col("price")
        )
        
        df = df.withColumn(
            "order_value_category",
            F.when(F.col("order_value") < 50, "Low")
            .when(F.col("order_value") < 200, "Medium")
            .when(F.col("order_value") < 500, "High")
            .otherwise("Premium")
        )
        
        # Add date partitions
        df = df.withColumn("year", F.year(F.col("order_date")))
        df = df.withColumn("month", F.format_string("%02d", F.month(F.col("order_date"))))
        df = df.withColumn("day", F.format_string("%02d", F.dayofmonth(F.col("order_date"))))
    
    print(f"✅ Transformed {df.count()} records for {table_name}")
    
    # Convert back to DynamicFrame
    return DynamicFrame.fromDF(df, glueContext, f"transformed_{table_name}")

def load_to_s3_incremental(dynamic_frame, target_path, table_name):
    """Load incremental data to S3 in append mode with partitioning"""
    
    df = dynamic_frame.toDF()
    
    if df.count() == 0:
        print(f"ℹ️  No data to load for {table_name}")
        return
    
    print(f"📤 Loading {df.count()} records to S3: {target_path}")
    
    if table_name == "orders":
        # Write with partitioning for orders (append mode for incremental)
        df.write.mode("append").partitionBy("year", "month", "day").parquet(target_path)
        
    else:
        # For customers, partition by processing date since updates can happen
        df = df.withColumn("processing_year", F.year(F.current_date()))
        df = df.withColumn("processing_month", F.format_string("%02d", F.month(F.current_date())))
        df = df.withColumn("processing_day", F.format_string("%02d", F.dayofmonth(F.current_date())))
        
        # Use append mode for incremental processing
        df.write.mode("append").partitionBy("processing_year", "processing_month", "processing_day").parquet(target_path)
    
    print(f"✅ Successfully loaded {table_name} data to S3")

def main():
    """Main ETL process with incremental logic"""
    
    source_table = args['source_table']
    target_path = args['target_path']
    connection_name = args['connection_name']
    
    # Extract S3 bucket from target path
    s3_bucket = target_path.replace("s3://", "").split("/")[0]
    
    print(f"🚀 Starting incremental ETL for table: {source_table}")
    print(f"📍 Target path: {target_path}")
    print(f"🪣 S3 bucket: {s3_bucket}")
    
    try:
        # Get last processed timestamp
        last_timestamp = get_last_processed_timestamp(s3_bucket, source_table)
        
        # Extract incremental data
        print("🔄 Starting incremental data extraction...")
        incremental_data = extract_from_rds_incremental(source_table, connection_name, last_timestamp)
        
        record_count = incremental_data.count()
        
        if record_count > 0:
            print(f"📊 Processing {record_count} incremental records")
            
            # Transform
            print("🔧 Starting data transformation...")
            transformed_data = transform_data(incremental_data, source_table)
            
            # Load incrementally
            print("📤 Starting incremental data load to S3...")
            load_to_s3_incremental(transformed_data, target_path, source_table)
            
            # Update timestamp for next run
            current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_last_processed_timestamp(s3_bucket, source_table, current_timestamp)
            
            print(f"✅ Incremental ETL completed successfully for {source_table}")
            print(f"📈 Records processed: {record_count}")
            
            # Enable job bookmarking for Glue's built-in incremental processing
            job.commit()
            
        else:
            print(f"ℹ️  No new records found for {source_table} since {last_timestamp}")
            print("✅ ETL job completed - no processing needed")
            
    except Exception as e:
        print(f"❌ ETL failed for {source_table}: {str(e)}")
        raise e

if __name__ == "__main__":
    main()
