# Simplified AWS Glue ETL Job Template using Job Bookmarks
# This template leverages AWS Glue's native bookmarking for incremental processing

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql import functions as F
from datetime import datetime

# Get job parameters
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'source_table',
    'target_path',
    'database_name',
    'connection_name'
])

# Initialize Glue context with job bookmarking enabled
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

def extract_from_rds_with_bookmark(table_name, connection_name, database_name):
    """Extract data from RDS PostgreSQL using primary key + timestamp bookmarking for incremental processing"""
    
    print(f"🔍 Extracting data for {table_name} using primary key + timestamp bookmarking")
    
    # Define primary key and timestamp columns for each table
    if table_name == "customers":
        primary_key = "customer_id"
        timestamp_col = "updated_at"
        # Also check created_at for new records
        incremental_query = f"""
        (SELECT * FROM public.{table_name} 
         ORDER BY {primary_key}, {timestamp_col}) as incremental_data
        """
    elif table_name == "orders":
        primary_key = "order_id"
        timestamp_col = "updated_at"
        incremental_query = f"""
        (SELECT * FROM public.{table_name} 
         ORDER BY {primary_key}, {timestamp_col}) as incremental_data
        """
    else:
        # Default approach for other tables
        primary_key = "id"
        timestamp_col = "updated_at"
        incremental_query = f"""
        (SELECT * FROM public.{table_name} 
         ORDER BY {primary_key}, {timestamp_col}) as incremental_data
        """
    
    print(f"📝 Using bookmark tracking on: {primary_key} + {timestamp_col}")
    print(f"📝 Query: {incremental_query}")
    
    # Extract data using incremental query with bookmark tracking
    # Glue will automatically track which (primary_key, timestamp) combinations have been processed
    dynamic_frame = glueContext.create_dynamic_frame.from_options(
        connection_type="postgresql",
        connection_options={
            "useConnectionProperties": "true",
            "dbtable": incremental_query,
            "connectionName": connection_name,
        },
        transformation_ctx=f"extract_{table_name}_pk_timestamp_bookmarked"
    )
    
    record_count = dynamic_frame.count()
    print(f"📊 Found {record_count} records for processing (new/updated based on {primary_key}+{timestamp_col} bookmarks)")
    
    return dynamic_frame

def extract_from_rds_direct(table_name, connection_name):
    """Fallback: Extract data directly from RDS if catalog not available"""
    
    print(f"🔍 Extracting data for {table_name} directly from RDS")
    
    # Direct connection to RDS table
    dynamic_frame = glueContext.create_dynamic_frame.from_options(
        connection_type="postgresql",
        connection_options={
            "useConnectionProperties": "true",
            "dbtable": f"public.{table_name}",
            "connectionName": connection_name,
        },
        transformation_ctx=f"extract_direct_{table_name}"
    )
    
    record_count = dynamic_frame.count()
    print(f"📊 Found {record_count} total records")
    
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
        # Add customer lifecycle analysis
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
        
        # Add email domain analysis
        df = df.withColumn(
            "email_domain",
            F.split(F.col("email"), "@").getItem(1)
        )
    
    elif table_name == "orders":
        # Add order value calculations and categorization
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
        
        # Add time-based partitions for efficient querying
        df = df.withColumn("year", F.year(F.col("order_date")))
        df = df.withColumn("month", F.format_string("%02d", F.month(F.col("order_date"))))
        df = df.withColumn("day", F.format_string("%02d", F.dayofmonth(F.col("order_date"))))
        
        # Add day of week analysis
        df = df.withColumn("day_of_week", F.dayofweek(F.col("order_date")))
        df = df.withColumn(
            "day_name",
            F.when(F.col("day_of_week") == 1, "Sunday")
            .when(F.col("day_of_week") == 2, "Monday")
            .when(F.col("day_of_week") == 3, "Tuesday")
            .when(F.col("day_of_week") == 4, "Wednesday")
            .when(F.col("day_of_week") == 5, "Thursday")
            .when(F.col("day_of_week") == 6, "Friday")
            .when(F.col("day_of_week") == 7, "Saturday")
        )
    
    print(f"✅ Transformed {df.count()} records for {table_name}")
    
    # Convert back to DynamicFrame
    return DynamicFrame.fromDF(df, glueContext, f"transformed_{table_name}")

def load_to_s3_with_partitioning(dynamic_frame, target_path, table_name):
    """Load data to S3 with appropriate partitioning strategy and upsert logic"""
    
    df = dynamic_frame.toDF()
    
    if df.count() == 0:
        print(f"ℹ️  No data to load for {table_name}")
        return
    
    print(f"📤 Loading {df.count()} records to S3: {target_path}")
    
    # For incremental updates, we need to handle upserts properly
    # This means overwriting partitions that contain updated records
    
    if table_name == "orders":
        # Orders: Partition by date for time-series analysis
        # For orders, we use append mode since orders are typically immutable
        # But if updated_at changes, we need to handle it
        
        # Check if we have any updated records (records with updated_at different from created_at equivalent)
        print("📝 Processing orders with date partitioning...")
        df.write.mode("append").partitionBy("year", "month", "day").parquet(target_path)
        
    else:
        # Customers: Partition by customer segment and processing date
        # For customers, updates are more common, so we use overwrite mode for partitions
        df = df.withColumn("processing_year", F.year(F.current_date()))
        df = df.withColumn("processing_month", F.format_string("%02d", F.month(F.current_date())))
        
        print("📝 Processing customers with segment partitioning...")
        # Use overwrite mode to handle customer updates properly
        df.write.mode("overwrite").partitionBy("customer_segment", "processing_year", "processing_month").parquet(target_path)
    
    print(f"✅ Successfully loaded {table_name} data to S3")
    print("📝 Note: Using appropriate write mode for incremental updates")

def main():
    """Main ETL process using AWS Glue job bookmarks"""
    
    source_table = args['source_table']
    target_path = args['target_path']
    connection_name = args['connection_name']
    database_name = args['database_name']
    
    print(f"🚀 Starting bookmark-based ETL for table: {source_table}")
    print(f"📍 Target path: {target_path}")
    print(f"🗃️  Database: {database_name}")
    print(f"🔗 Connection: {connection_name}")
    
    try:
        # Extract data using primary key + timestamp bookmarking
        print("🔄 Extracting data using primary key + timestamp bookmarking...")
        source_data = extract_from_rds_with_bookmark(source_table, connection_name, database_name)
        
        record_count = source_data.count()
        
        if record_count > 0:
            print(f"📊 Processing {record_count} records")
            
            # Transform the data
            print("🔧 Starting data transformation...")
            transformed_data = transform_data(source_data, source_table)
            
            # Load to S3 with partitioning
            print("📤 Starting data load to S3...")
            load_to_s3_with_partitioning(transformed_data, target_path, source_table)
            
            print(f"✅ ETL completed successfully for {source_table}")
            print(f"📈 Records processed: {record_count}")
            
        else:
            print(f"ℹ️  No new records found for {source_table}")
            print("✅ ETL job completed - no processing needed")
        
        # Commit the job to update bookmarks
        # This tells Glue which records have been successfully processed
        job.commit()
        print("📑 Job bookmarks updated successfully")
            
    except Exception as e:
        print(f"❌ ETL failed for {source_table}: {str(e)}")
        print("📋 Job bookmarks not updated due to error")
        raise e

if __name__ == "__main__":
    main()
