#!/usr/bin/env python3
"""
Script to test Athena queries after deployment
"""

import boto3
import time
import sys

def run_athena_query(query, database, workgroup, output_location):
    """Execute an Athena query and return results"""
    
    client = boto3.client('athena', region_name='us-east-1')
    
    # Start query execution
    response = client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={
            'Database': database
        },
        WorkGroup=workgroup,
        ResultConfiguration={
            'OutputLocation': output_location
        }
    )
    
    query_execution_id = response['QueryExecutionId']
    print(f"Query started with ID: {query_execution_id}")
    
    # Wait for query to complete
    while True:
        response = client.get_query_execution(QueryExecutionId=query_execution_id)
        status = response['QueryExecution']['Status']['State']
        
        if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
            break
        
        print(f"Query status: {status}")
        time.sleep(2)
    
    if status == 'SUCCEEDED':
        print("✅ Query succeeded!")
        
        # Get results
        results = client.get_query_results(QueryExecutionId=query_execution_id)
        
        # Print column headers
        columns = [col['Label'] for col in results['ResultSet']['ResultSetMetadata']['ColumnInfo']]
        print("\n" + " | ".join(columns))
        print("-" * (len(" | ".join(columns))))
        
        # Print data rows
        for row in results['ResultSet']['Rows'][1:10]:  # Skip header row, show first 10 results
            values = [cell.get('VarCharValue', 'NULL') for cell in row['Data']]
            print(" | ".join(values))
        
        total_rows = len(results['ResultSet']['Rows']) - 1
        if total_rows > 10:
            print(f"... and {total_rows - 10} more rows")
        
        return True
    else:
        error_message = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
        print(f"❌ Query failed: {error_message}")
        return False

def main():
    """Main function to test Athena queries"""
    
    if len(sys.argv) != 4:
        print("Usage: python test_athena.py <database_name> <workgroup_name> <s3_bucket_name>")
        sys.exit(1)
    
    database = sys.argv[1]
    workgroup = sys.argv[2]
    s3_bucket = sys.argv[3]
    output_location = f"s3://{s3_bucket}/athena-results/"
    
    print(f"🔍 Testing Athena Queries")
    print(f"Database: {database}")
    print(f"Workgroup: {workgroup}")
    print(f"Output Location: {output_location}")
    print("=" * 50)
    
    # Test queries
    queries = [
        {
            'name': 'Customer Count',
            'query': 'SELECT COUNT(*) as total_customers FROM customers;'
        },
        {
            'name': 'Order Count',
            'query': 'SELECT COUNT(*) as total_orders FROM orders;'
        },
        {
            'name': 'Total Revenue',
            'query': 'SELECT SUM(quantity * price) as total_revenue FROM orders;'
        },
        {
            'name': 'Top 5 Customers by Spending',
            'query': '''
                SELECT 
                    c.name,
                    c.email,
                    COUNT(o.order_id) as total_orders,
                    SUM(o.quantity * o.price) as total_spent
                FROM customers c
                LEFT JOIN orders o ON c.customer_id = o.customer_id
                GROUP BY c.customer_id, c.name, c.email
                ORDER BY total_spent DESC
                LIMIT 5;
            '''
        },
        {
            'name': 'Top 5 Products by Revenue',
            'query': '''
                SELECT 
                    product_name,
                    COUNT(order_id) as order_count,
                    SUM(quantity) as total_quantity,
                    SUM(quantity * price) as total_revenue
                FROM orders
                GROUP BY product_name
                ORDER BY total_revenue DESC
                LIMIT 5;
            '''
        }
    ]
    
    # Configure boto3 to use the test-prod profile
    session = boto3.Session(profile_name='test-prod')
    
    success_count = 0
    for i, query_info in enumerate(queries, 1):
        print(f"\n{i}. Testing: {query_info['name']}")
        print("-" * 40)
        
        try:
            if run_athena_query(query_info['query'], database, workgroup, output_location):
                success_count += 1
        except Exception as e:
            print(f"❌ Error running query: {e}")
        
        if i < len(queries):
            print("\nWaiting 3 seconds before next query...")
            time.sleep(3)
    
    print(f"\n📊 Test Summary")
    print("=" * 50)
    print(f"Total queries: {len(queries)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(queries) - success_count}")
    
    if success_count == len(queries):
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Check the error messages above.")

if __name__ == "__main__":
    main()
