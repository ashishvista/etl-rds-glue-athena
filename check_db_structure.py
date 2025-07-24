#!/usr/bin/env python3
import psycopg2
import sys

def check_database_structure():
    """Check the database structure and table information"""
    
    # Database connection parameters
    db_config = {
        'host': 'data-analytics-postgres-v2.ccbsg6ya6wfa.us-east-1.rds.amazonaws.com',
        'port': 5432,
        'database': 'analytics_db',
        'user': 'analytics_user',
        'password': 'ChangeMe123!'
    }
    
    try:
        print("🔗 Connecting to database...")
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Check current database
        cursor.execute("SELECT current_database();")
        current_db = cursor.fetchone()[0]
        print(f"📊 Current database: {current_db}")
        
        # Check current schema
        cursor.execute("SELECT current_schema();")
        current_schema = cursor.fetchone()[0]
        print(f"📋 Current schema: {current_schema}")
        
        # List all schemas
        cursor.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
            ORDER BY schema_name;
        """)
        schemas = cursor.fetchall()
        print(f"📁 Available schemas: {[s[0] for s in schemas]}")
        
        # List all tables in current schema
        cursor.execute("""
            SELECT table_name, table_schema
            FROM information_schema.tables 
            WHERE table_type = 'BASE TABLE'
            AND table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
            ORDER BY table_schema, table_name;
        """)
        tables = cursor.fetchall()
        print(f"📋 Available tables:")
        for table_name, schema_name in tables:
            print(f"   - {schema_name}.{table_name}")
        
        # Check specific tables we need
        for table in ['customers', 'orders']:
            cursor.execute(f"""
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_name = '{table}'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()
            
            if columns:
                print(f"\n📊 Table '{table}' structure:")
                for col_name, data_type in columns:
                    print(f"   - {col_name}: {data_type}")
                
                # Count records
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                print(f"   📈 Record count: {count}")
            else:
                print(f"\n❌ Table '{table}' not found")
        
        cursor.close()
        conn.close()
        print("\n✅ Database structure check completed!")
        
    except Exception as e:
        print(f"❌ Error checking database: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    check_database_structure()
