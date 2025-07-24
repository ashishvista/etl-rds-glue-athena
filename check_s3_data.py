#!/usr/bin/env python3
import boto3
import json

def check_s3_data():
    """Check what data was loaded to S3 by the ETL jobs"""
    
    s3_client = boto3.client('s3')
    bucket_name = 'data-analytics-data-lake-wsvnlynm'
    
    print(f"🪣 Checking S3 bucket: {bucket_name}")
    print("="*50)
    
    try:
        # List all objects in the bucket
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        
        if 'Contents' not in response:
            print("❌ No objects found in bucket")
            return
            
        objects = response['Contents']
        total_size = 0
        file_count = 0
        
        # Group by prefix (table/folder)
        folders = {}
        
        for obj in objects:
            key = obj['Key']
            size = obj['Size']
            modified = obj['LastModified']
            
            total_size += size
            file_count += 1
            
            # Extract folder/table name
            folder = key.split('/')[0] if '/' in key else 'root'
            if folder not in folders:
                folders[folder] = {'files': [], 'total_size': 0}
            
            folders[folder]['files'].append({
                'key': key,
                'size': size,
                'modified': modified.strftime('%Y-%m-%d %H:%M:%S')
            })
            folders[folder]['total_size'] += size
        
        print(f"📊 Total files: {file_count}")
        print(f"📦 Total size: {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)")
        print()
        
        # Show details by folder
        for folder, data in sorted(folders.items()):
            print(f"📁 {folder}/ ({len(data['files'])} files, {data['total_size']:,} bytes)")
            
            # Show first few files
            for file_info in sorted(data['files'], key=lambda x: x['modified'], reverse=True)[:5]:
                print(f"   📄 {file_info['key']}")
                print(f"      📦 {file_info['size']:,} bytes")
                print(f"      📅 {file_info['modified']}")
                print()
            
            if len(data['files']) > 5:
                print(f"   ... and {len(data['files']) - 5} more files")
                print()
        
        # Check for ETL metadata
        print("📋 ETL Metadata:")
        metadata_objects = [obj for obj in objects if 'etl-metadata' in obj['Key']]
        if metadata_objects:
            for obj in metadata_objects:
                print(f"   🔖 {obj['Key']} ({obj['Size']} bytes)")
                
                # Try to read timestamp files
                if obj['Key'].endswith('.txt'):
                    try:
                        content = s3_client.get_object(Bucket=bucket_name, Key=obj['Key'])
                        timestamp = content['Body'].read().decode('utf-8').strip()
                        print(f"      📅 Content: {timestamp}")
                    except Exception as e:
                        print(f"      ❌ Could not read: {e}")
        else:
            print("   ℹ️  No ETL metadata found")
        
        print("\n✅ S3 data check completed!")
        
    except Exception as e:
        print(f"❌ Error checking S3: {e}")

if __name__ == "__main__":
    check_s3_data()
