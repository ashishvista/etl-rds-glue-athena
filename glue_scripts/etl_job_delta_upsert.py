# AWS Glue ETL Job Template with Delta Lake for UPSERT operations
# This template uses AWS Glue native bookmarks + Delta Lake for proper incremental processing
# Handles both new records and updates with ACID transactions

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql import functions as F

# Get job parameters
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'source_table',
    'target_path',
    'database_name',
    'connection_name'
])

# Initialize Glue context first
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

job = Job(glueContext)
job.init(args['JOB_NAME'], args)

def extract_with_native_bookmarks(table_name, connection_name):
    """
    Extract data using AWS Glue native bookmark functionality
    This automatically handles incremental processing for both new records and updates
    """
    
    print(f"🔍 Starting incremental extraction for {table_name} using native bookmarks")
    
    # Define bookmark configuration for each table
    if table_name == "customers":
        dbtable = "public.customers"
        bookmark_keys = ["customer_id", "updated_at"]
        primary_key = "customer_id"
    elif table_name == "orders":
        dbtable = "public.orders"
        bookmark_keys = ["order_id", "updated_at"]
        primary_key = "order_id"
    else:
        dbtable = f"public.{table_name}"
        bookmark_keys = ["id", "updated_at"]
        primary_key = "id"
    
    print(f"📋 Table: {dbtable}")
    print(f"🔑 Bookmark keys: {bookmark_keys}")
    print(f"🗝️  Primary key: {primary_key}")
    
    # Use AWS Glue's native bookmarking with jobBookmarkKeys
    dynamic_frame = glueContext.create_dynamic_frame.from_options(
        connection_type="postgresql",
        connection_options={
            "useConnectionProperties": "true",
            "dbtable": dbtable,
            "connectionName": connection_name,
        },
        additional_options={
            "jobBookmarkKeys": bookmark_keys,
            "jobBookmarkKeysSortOrder": "asc"
        },
        transformation_ctx=f"extract_{table_name}_with_bookmarks"
    )
    
    record_count = dynamic_frame.count()
    print(f"📊 Extracted {record_count} new/updated records using bookmark keys: {bookmark_keys}")
    
    return dynamic_frame, primary_key

def transform_data(dynamic_frame, table_name):
    """Apply transformations and prepare data for Delta Lake upsert"""
    
    print(f"🔄 Applying transformations for {table_name}")
    
    # Convert to DataFrame for easier manipulation
    df = dynamic_frame.toDF()
    
    # Add processing metadata
    df = df.withColumn("etl_processed_at", F.current_timestamp()) \
           .withColumn("etl_job_run_id", F.lit(args['JOB_NAME'] + "_" + str(int(F.unix_timestamp().collect()[0][0]))))
    
    # Add year/month/day columns for partitioning (derived from updated_at)
    if "updated_at" in df.columns:
        df = df.withColumn("year", F.year("updated_at")) \
               .withColumn("month", F.month("updated_at")) \
               .withColumn("day", F.dayofmonth("updated_at"))
    else:
        # Fallback to processing time if updated_at not available
        df = df.withColumn("year", F.year("etl_processed_at")) \
               .withColumn("month", F.month("etl_processed_at")) \
               .withColumn("day", F.dayofmonth("etl_processed_at"))
    
    print(f"✅ Transformations completed for {table_name}")
    print(f"📏 Transformed DataFrame schema:")
    df.printSchema()
    
    return df

def upsert_to_delta_lake(df, target_path, table_name, primary_key):
    """
    Perform UPSERT operation to Delta Lake table using Spark SQL MERGE
    """
    
    print(f"🔄 Starting Delta Lake UPSERT for {table_name}")
    print(f"📂 Target path: {target_path}")
    print(f"🗝️  Primary key for merge: {primary_key}")
    
    delta_table_path = f"{target_path}/delta"
    
    try:
        # Register new data as a temp view
        df.createOrReplaceTempView("source_table")
        
        # If Delta table does not exist, write initial data
        try:
            spark.read.format("delta").load(delta_table_path)
            table_exists = True
        except Exception:
            table_exists = False
        
        if not table_exists:
            print(f"📝 Creating new Delta table at {delta_table_path}")
            df.write.format("delta").mode("overwrite").partitionBy("year", "month", "day").save(delta_table_path)
            print(f"✅ New Delta table created successfully")
        else:
            print(f"🔄 Performing UPSERT operation with MERGE INTO ...")
            merge_sql = f"""
            MERGE INTO delta.`{delta_table_path}` AS target
            USING source_table AS source
            ON target.{primary_key} = source.{primary_key}
            WHEN MATCHED THEN UPDATE SET *
            WHEN NOT MATCHED THEN INSERT *
            """
            spark.sql(merge_sql)
            print(f"✅ UPSERT completed successfully")
        
        # Read back the final table for verification
        final_df = spark.read.format("delta").load(delta_table_path)
        final_count = final_df.count()
        print(f"📊 Final table record count: {final_count}")
        
        # Show some sample records
        print(f"📋 Sample records from final table:")
        final_df.orderBy(F.desc("updated_at")).limit(5).show(truncate=False)
        
        return final_count
        
    except Exception as e:
        print(f"❌ Error during Delta Lake UPSERT: {str(e)}")
        raise e

def create_symlink_manifest(delta_table_path, target_path):
    """
    Create symlink manifest for Athena compatibility with Delta Lake
    """
    
    print(f"🔗 Creating symlink manifest for Athena compatibility")
    
    try:
        # Get the latest files from Delta table
        df = spark.read.format("delta").load(delta_table_path)
        latest_files = df.inputFiles()
        
        # Create symlink manifest
        symlink_path = f"{target_path}/symlink_format_manifest"
        
        # Write manifest file
        manifest_content = "\n".join(latest_files)
        
        # Use Spark to write the manifest
        spark.sparkContext.parallelize([manifest_content]).coalesce(1) \
            .saveAsTextFile(f"{symlink_path}/manifest")
        
        print(f"✅ Symlink manifest created at {symlink_path}")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not create symlink manifest: {str(e)}")
        print(f"   Athena queries may need to use Delta Lake native support")

def optimize_delta_table(delta_table_path, table_name):
    """
    Optimize Delta Lake table by compacting small files (no Z-ORDER in Glue native)
    """
    
    print(f"🔧 Optimizing Delta table for {table_name}")
    
    try:
        df = spark.read.format("delta").load(delta_table_path)
        file_count = len(df.inputFiles())
        if file_count > 10:
            print(f"📦 Compacting {file_count} files...")
            df.repartition(4).write.format("delta").mode("overwrite").partitionBy("year", "month", "day").option("overwriteSchema", "true").save(delta_table_path)
            print(f"✅ Delta table compaction completed")
        else:
            print(f"ℹ️  File count ({file_count}) is acceptable, skipping compaction")
    
    except Exception as e:
        print(f"⚠️  Warning: Delta table optimization failed: {str(e)}")

def main():
    """Main ETL process with Delta Lake UPSERT functionality only"""
    
    table_name = args['source_table']
    target_path = args['target_path']
    connection_name = args['connection_name']
    
    print(f"🚀 Starting Delta Lake ETL job for table: {table_name}")
    print(f"📂 Target S3 path: {target_path}")
    print(f"🔗 Connection: {connection_name}")
    
    try:
        # Step 1: Extract data using native bookmarks
        source_data, primary_key = extract_with_native_bookmarks(table_name, connection_name)
        
        # Check if we have any data to process
        if source_data.count() == 0:
            print("ℹ️  No new or updated records found. Job completed successfully.")
            job.commit()
            return
        
        # Step 2: Transform data
        transformed_df = transform_data(source_data, table_name)
        
        # Step 3: UPSERT to Delta Lake
        final_count = upsert_to_delta_lake(transformed_df, target_path, table_name, primary_key)
        
        # Step 4: Create symlink manifest for Athena (optional)
        delta_table_path = f"{target_path}/delta"
        create_symlink_manifest(delta_table_path, target_path)
        
        # Step 5: Optimize Delta table (optional, but recommended)
        optimize_delta_table(delta_table_path, table_name)
        
        print(f"🎉 Delta Lake ETL job completed successfully for {table_name}")
        print(f"📊 Final record count: {final_count}")
        
    except Exception as e:
        print(f"❌ Error in Delta Lake ETL job for {table_name}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise e
    
    finally:
        # Commit the job to update bookmarks
        job.commit()
