#!/usr/bin/env python3
"""
Script to run Glue ETL jobs and monitor their progress
"""

import boto3
import time
import sys
import json
from datetime import datetime

def run_glue_job(job_name, profile_name='test-prod'):
    """Start a Glue job and return the job run ID"""
    
    session = boto3.Session(profile_name=profile_name)
    glue_client = session.client('glue', region_name='us-east-1')
    
    try:
        response = glue_client.start_job_run(JobName=job_name)
        job_run_id = response['JobRunId']
        print(f"✅ Started Glue job: {job_name}")
        print(f"📋 Job Run ID: {job_run_id}")
        return job_run_id
    except Exception as e:
        print(f"❌ Failed to start job {job_name}: {str(e)}")
        return None

def monitor_job(job_name, job_run_id, profile_name='test-prod'):
    """Monitor a Glue job until completion"""
    
    session = boto3.Session(profile_name=profile_name)
    glue_client = session.client('glue', region_name='us-east-1')
    
    print(f"🔍 Monitoring job: {job_name} (Run ID: {job_run_id})")
    
    while True:
        try:
            response = glue_client.get_job_run(JobName=job_name, RunId=job_run_id)
            job_run = response['JobRun']
            
            job_state = job_run['JobRunState']
            print(f"📊 Job Status: {job_state}")
            
            if job_state in ['SUCCEEDED', 'FAILED', 'STOPPED', 'TIMEOUT']:
                break
            
            time.sleep(30)  # Wait 30 seconds before checking again
            
        except Exception as e:
            print(f"❌ Error monitoring job: {str(e)}")
            break
    
    # Print final status and metrics
    if job_state == 'SUCCEEDED':
        print(f"✅ Job {job_name} completed successfully!")
        
        # Print execution metrics
        if 'ExecutionTime' in job_run:
            execution_time = job_run['ExecutionTime']
            print(f"⏱️  Execution Time: {execution_time} seconds")
        
        if 'MaxCapacity' in job_run:
            max_capacity = job_run['MaxCapacity']
            print(f"💻 DPU Usage: {max_capacity}")
            
    else:
        print(f"❌ Job {job_name} failed with status: {job_state}")
        if 'ErrorMessage' in job_run:
            print(f"💥 Error: {job_run['ErrorMessage']}")
    
    return job_state == 'SUCCEEDED'

def run_crawler(crawler_name, profile_name='test-prod'):
    """Start a Glue crawler and return the crawler run ID"""
    
    session = boto3.Session(profile_name=profile_name)
    glue_client = session.client('glue', region_name='us-east-1')
    
    try:
        response = glue_client.start_crawler(Name=crawler_name)
        print(f"✅ Started Glue crawler: {crawler_name}")
        return True
    except Exception as e:
        print(f"❌ Failed to start crawler {crawler_name}: {str(e)}")
        return False

def monitor_crawler(crawler_name, profile_name='test-prod'):
    """Monitor a Glue crawler until completion"""
    
    session = boto3.Session(profile_name=profile_name)
    glue_client = session.client('glue', region_name='us-east-1')
    
    print(f"🔍 Monitoring crawler: {crawler_name}")
    
    while True:
        try:
            response = glue_client.get_crawler(Name=crawler_name)
            crawler = response['Crawler']
            
            crawler_state = crawler['State']
            print(f"📊 Crawler Status: {crawler_state}")
            
            if crawler_state in ['READY', 'STOPPING']:
                break
            
            time.sleep(30)  # Wait 30 seconds before checking again
            
        except Exception as e:
            print(f"❌ Error monitoring crawler: {str(e)}")
            break
    
    # Print final status
    if crawler_state == 'READY':
        print(f"✅ Crawler {crawler_name} completed successfully!")
        
        # Show tables created/updated
        if 'LastCrawl' in crawler:
            last_crawl = crawler['LastCrawl']
            if 'Status' in last_crawl:
                print(f"📈 Last crawl status: {last_crawl['Status']}")
            if 'TablesCreated' in last_crawl:
                print(f"📋 Tables created: {last_crawl['TablesCreated']}")
            if 'TablesUpdated' in last_crawl:
                print(f"🔄 Tables updated: {last_crawl['TablesUpdated']}")
    else:
        print(f"❌ Crawler {crawler_name} ended with status: {crawler_state}")
    
    return crawler_state == 'READY'

def list_glue_jobs(profile_name='test-prod'):
    """List all available Glue jobs"""
    
    session = boto3.Session(profile_name=profile_name)
    glue_client = session.client('glue', region_name='us-east-1')
    
    try:
        response = glue_client.get_jobs()
        jobs = response['Jobs']
        
        print("📋 Available Glue Jobs:")
        print("-" * 40)
        for job in jobs:
            job_name = job['Name']
            job_role = job['Role']
            created_on = job['CreatedOn'].strftime('%Y-%m-%d %H:%M:%S')
            print(f"• {job_name}")
            print(f"  Role: {job_role}")
            print(f"  Created: {created_on}")
            print()
            
    except Exception as e:
        print(f"❌ Error listing jobs: {str(e)}")

def main():
    """Main function"""
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 run_glue_jobs.py list                    # List all jobs and crawlers")
        print("  python3 run_glue_jobs.py run <job_name>          # Run a specific job")
        print("  python3 run_glue_jobs.py run-all                 # Run all ETL jobs")
        print("  python3 run_glue_jobs.py run-crawler <name>      # Run a specific crawler")
        print("  python3 run_glue_jobs.py run-pipeline            # Run ETL jobs + crawler")
        print("  python3 run_glue_jobs.py monitor <job_name> <run_id>  # Monitor a job")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        list_glue_jobs()
        
    elif command == "run" and len(sys.argv) == 3:
        job_name = sys.argv[2]
        job_run_id = run_glue_job(job_name)
        
        if job_run_id:
            monitor_job(job_name, job_run_id)
            
    elif command == "run-crawler" and len(sys.argv) == 3:
        crawler_name = sys.argv[2]
        if run_crawler(crawler_name):
            monitor_crawler(crawler_name)
            
    elif command == "run-all":
        # Run both ETL jobs
        jobs_to_run = [
            "data-analytics-customers-etl",
            "data-analytics-orders-etl"
        ]
        
        job_runs = []
        
        # Start all jobs
        for job_name in jobs_to_run:
            job_run_id = run_glue_job(job_name)
            if job_run_id:
                job_runs.append((job_name, job_run_id))
        
        # Monitor all jobs
        all_succeeded = True
        for job_name, job_run_id in job_runs:
            print(f"\n🔍 Monitoring {job_name}...")
            success = monitor_job(job_name, job_run_id)
            if not success:
                all_succeeded = False
        
        if all_succeeded:
            print("\n✅ All ETL jobs completed successfully!")
        else:
            print("\n❌ Some ETL jobs failed")
            
    elif command == "run-pipeline":
        # Run complete pipeline: ETL jobs + crawler
        print("🚀 Starting complete data pipeline...")
        
        # First run ETL jobs
        jobs_to_run = [
            "data-analytics-customers-etl",
            "data-analytics-orders-etl"
        ]
        
        job_runs = []
        
        # Start all jobs
        for job_name in jobs_to_run:
            job_run_id = run_glue_job(job_name)
            if job_run_id:
                job_runs.append((job_name, job_run_id))
        
        # Monitor all jobs
        all_succeeded = True
        for job_name, job_run_id in job_runs:
            print(f"\n🔍 Monitoring {job_name}...")
            success = monitor_job(job_name, job_run_id)
            if not success:
                all_succeeded = False
        
        # If ETL succeeded, run crawler
        if all_succeeded:
            print("\n🕷️ Starting crawler to update schema...")
            crawler_name = "data-analytics-crawler"
            if run_crawler(crawler_name):
                monitor_crawler(crawler_name)
            print("\n🎉 Complete pipeline finished!")
        else:
            print("\n❌ ETL jobs failed, skipping crawler")
            
    elif command == "monitor" and len(sys.argv) == 4:
        job_name = sys.argv[2]
        job_run_id = sys.argv[3]
        monitor_job(job_name, job_run_id)
        
    else:
        print("❌ Invalid command or arguments")
        sys.exit(1)

if __name__ == "__main__":
    main()
