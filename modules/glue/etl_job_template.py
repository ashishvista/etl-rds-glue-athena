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

# Initialize Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Enable job bookmarking for incremental processing
job.commit()

def extract_from_rds(table_name, connection_name):
    """Extract data from RDS PostgreSQL"""
    
    # Read from PostgreSQL using Glue connection
    dynamic_frame = glueContext.create_dynamic_frame.from_options(
        connection_type="postgresql",
        connection_options={
            "useConnectionProperties": "true",
            "dbtable": table_name,
            "connectionName": connection_name,
        },
        transformation_ctx=f"extract_{table_name}"
    )
    
    return dynamic_frame

def transform_data(dynamic_frame, table_name):
    """Apply transformations to the data"""
    
    # Convert to Spark DataFrame for transformations
    df = dynamic_frame.toDF()
    
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
    
    # Convert back to DynamicFrame
    return DynamicFrame.fromDF(df, glueContext, f"transformed_{table_name}")

def load_to_s3(dynamic_frame, target_path, table_name):
    """Load data to S3 in Parquet format with partitioning"""
    
    if table_name == "orders":
        # Write with partitioning for orders
        glueContext.write_dynamic_frame.from_options(
            frame=dynamic_frame,
            connection_type="s3",
            connection_options={
                "path": target_path,
                "partitionKeys": ["year", "month", "day"]
            },
            format="parquet",
            transformation_ctx=f"load_{table_name}"
        )
    else:
        # Write without partitioning for customers (smaller dataset)
        # But still organize by date for incremental updates
        df = dynamic_frame.toDF()
        df = df.withColumn("year", F.year(F.current_date()))
        df = df.withColumn("month", F.format_string("%02d", F.month(F.current_date())))
        df = df.withColumn("day", F.format_string("%02d", F.dayofmonth(F.current_date())))
        
        partitioned_frame = DynamicFrame.fromDF(df, glueContext, f"partitioned_{table_name}")
        
        glueContext.write_dynamic_frame.from_options(
            frame=partitioned_frame,
            connection_type="s3",
            connection_options={
                "path": target_path,
                "partitionKeys": ["year", "month", "day"]
            },
            format="parquet",
            transformation_ctx=f"load_{table_name}"
        )

def main():
    """Main ETL process"""
    
    source_table = args['source_table']
    target_path = args['target_path']
    connection_name = args['connection_name']
    
    print(f"Starting ETL for table: {source_table}")
    print(f"Target path: {target_path}")
    
    try:
        # Extract
        print("Starting data extraction...")
        raw_data = extract_from_rds(source_table, connection_name)
        
        # Show some statistics
        record_count = raw_data.count()
        print(f"Extracted {record_count} records from {source_table}")
        
        if record_count > 0:
            # Transform
            print("Starting data transformation...")
            transformed_data = transform_data(raw_data, source_table)
            
            # Load
            print("Starting data load to S3...")
            load_to_s3(transformed_data, target_path, source_table)
            
            print(f"ETL completed successfully for {source_table}")
            print(f"Records processed: {record_count}")
        else:
            print(f"No new records found for {source_table}")
            
    except Exception as e:
        print(f"ETL failed for {source_table}: {str(e)}")
        raise e

if __name__ == "__main__":
    main()

job.commit()
