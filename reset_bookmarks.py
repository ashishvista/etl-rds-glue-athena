#!/usr/bin/env python3
"""
Simple script to reset Glue job bookmarks
"""

import boto3

def reset_bookmarks():
    """Reset job bookmarks for ETL jobs"""
    
    # Use default credentials (no profile)
    glue_client = boto3.client('glue', region_name='us-east-1')
    
    jobs = ["data-analytics-customers-etl", "data-analytics-orders-etl"]
    
    print("🔄 Resetting job bookmarks...")
    
    for job_name in jobs:
        try:
            response = glue_client.reset_job_bookmark(JobName=job_name)
            print(f"✅ Reset bookmark for: {job_name}")
        except Exception as e:
            print(f"❌ Failed to reset bookmark for {job_name}: {str(e)}")
    
    print("✅ Bookmark reset completed!")

if __name__ == "__main__":
    reset_bookmarks()
