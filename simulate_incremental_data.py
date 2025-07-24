#!/usr/bin/env python3
"""
Script to simulate incremental data updates for testing ETL pipeline
"""

import psycopg2
import sys
import random
from datetime import datetime, timedelta

def connect_to_db(endpoint, db_name, username, password):
    """Connect to PostgreSQL database"""
    try:
        connection = psycopg2.connect(
            host=endpoint.split(':')[0],
            port=5432,
            database=db_name,
            user=username,
            password=password
        )
        print(f"✅ Connected to database: {db_name}")
        return connection
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return None

def add_new_customers(connection, count=5):
    """Add new customers to test incremental processing"""
    cursor = connection.cursor()
    
    new_customers = [
        ('Michael Zhang', 'michael.zhang@email.com'),
        ('Sarah Wilson', 'sarah.wilson@email.com'),
        ('David Kim', 'david.kim@email.com'),
        ('Emma Johnson', 'emma.johnson@email.com'),
        ('Ryan Chen', 'ryan.chen@email.com'),
        ('Lisa Anderson', 'lisa.anderson@email.com'),
        ('Alex Rodriguez', 'alex.rodriguez@email.com'),
        ('Maya Patel', 'maya.patel@email.com'),
        ('James Miller', 'james.miller@email.com'),
        ('Sophia Davis', 'sophia.davis@email.com')
    ]
    
    added_count = 0
    for i in range(min(count, len(new_customers))):
        name, email = new_customers[i]
        try:
            cursor.execute("""
                INSERT INTO customers (name, email) VALUES (%s, %s)
                ON CONFLICT (email) DO NOTHING
            """, (name, email))
            
            if cursor.rowcount > 0:
                added_count += 1
                
        except Exception as e:
            print(f"⚠️  Error adding customer {name}: {e}")
    
    connection.commit()
    cursor.close()
    print(f"➕ Added {added_count} new customers")
    return added_count

def update_existing_customers(connection, count=3):
    """Update existing customers to test incremental processing"""
    cursor = connection.cursor()
    
    try:
        # Get some existing customer IDs
        cursor.execute("SELECT customer_id, name, email FROM customers ORDER BY RANDOM() LIMIT %s", (count,))
        customers = cursor.fetchall()
        
        updated_count = 0
        for customer_id, old_name, email in customers:
            # Update customer name (simulate profile update)
            new_name = f"{old_name} (Updated)"
            
            cursor.execute("""
                UPDATE customers 
                SET name = %s, updated_at = CURRENT_TIMESTAMP 
                WHERE customer_id = %s
            """, (new_name, customer_id))
            
            if cursor.rowcount > 0:
                updated_count += 1
                print(f"🔄 Updated customer: {old_name} -> {new_name}")
        
        connection.commit()
        print(f"✏️  Updated {updated_count} existing customers")
        return updated_count
        
    except Exception as e:
        print(f"❌ Error updating customers: {e}")
        return 0
    finally:
        cursor.close()

def add_new_orders(connection, count=10):
    """Add new orders to test incremental processing"""
    cursor = connection.cursor()
    
    # Get available customer IDs
    cursor.execute("SELECT customer_id FROM customers")
    customer_ids = [row[0] for row in cursor.fetchall()]
    
    if not customer_ids:
        print("⚠️  No customers found, cannot add orders")
        return 0
    
    products = [
        ('MacBook Air M2', 1199.99),
        ('iPhone 15 Pro', 999.99),
        ('AirPods Pro', 249.99),
        ('iPad Pro', 799.99),
        ('Apple Watch Series 9', 399.99),
        ('Magic Keyboard', 179.99),
        ('Studio Display', 1599.99),
        ('Mac Studio', 2199.99),
        ('HomePod mini', 99.99),
        ('Apple Pencil', 129.99),
        ('USB-C Charger', 49.99),
        ('MagSafe Battery Pack', 99.99),
        ('Leather Case', 59.99),
        ('Screen Protector', 29.99),
        ('Wireless Charger', 39.99)
    ]
    
    added_count = 0
    for _ in range(count):
        customer_id = random.choice(customer_ids)
        product_name, base_price = random.choice(products)
        quantity = random.randint(1, 3)
        
        # Add some price variation
        price_variation = random.uniform(0.95, 1.05)
        price = round(base_price * price_variation, 2)
        
        # Random order date (last 3 days)
        days_ago = random.randint(0, 3)
        order_date = datetime.now().date() - timedelta(days=days_ago)
        
        try:
            cursor.execute("""
                INSERT INTO orders (customer_id, product_name, quantity, price, order_date)
                VALUES (%s, %s, %s, %s, %s)
            """, (customer_id, product_name, quantity, price, order_date))
            
            added_count += 1
            
        except Exception as e:
            print(f"⚠️  Error adding order: {e}")
    
    connection.commit()
    cursor.close()
    print(f"🛒 Added {added_count} new orders")
    return added_count

def update_existing_orders(connection, count=5):
    """Update existing orders to test incremental processing"""
    cursor = connection.cursor()
    
    try:
        # Get some recent orders
        cursor.execute("""
            SELECT order_id, product_name, quantity, price 
            FROM orders 
            WHERE order_date >= CURRENT_DATE - INTERVAL '7 days'
            ORDER BY RANDOM() 
            LIMIT %s
        """, (count,))
        orders = cursor.fetchall()
        
        updated_count = 0
        for order_id, product_name, old_quantity, old_price in orders:
            # Simulate quantity or price updates
            new_quantity = max(1, old_quantity + random.randint(-1, 2))
            price_change = random.uniform(0.9, 1.1)
            new_price = round(old_price * price_change, 2)
            
            cursor.execute("""
                UPDATE orders 
                SET quantity = %s, price = %s, updated_at = CURRENT_TIMESTAMP 
                WHERE order_id = %s
            """, (new_quantity, new_price, order_id))
            
            if cursor.rowcount > 0:
                updated_count += 1
                print(f"📝 Updated order {order_id}: {product_name} qty:{old_quantity}->{new_quantity} price:${old_price}->${new_price}")
        
        connection.commit()
        print(f"📋 Updated {updated_count} existing orders")
        return updated_count
        
    except Exception as e:
        print(f"❌ Error updating orders: {e}")
        return 0
    finally:
        cursor.close()

def show_recent_changes(connection):
    """Show recent data changes"""
    cursor = connection.cursor()
    
    print("\n📊 Recent Data Changes Summary:")
    print("=" * 50)
    
    try:
        # Recent customers
        cursor.execute("""
            SELECT COUNT(*) FROM customers 
            WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
               OR updated_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
        """)
        recent_customers = cursor.fetchone()[0]
        
        # Recent orders  
        cursor.execute("""
            SELECT COUNT(*) FROM orders 
            WHERE order_date >= CURRENT_DATE - INTERVAL '1 day'
               OR updated_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
        """)
        recent_orders = cursor.fetchone()[0]
        
        print(f"🧑‍🤝‍🧑 Customers modified in last hour: {recent_customers}")
        print(f"🛍️  Orders from last day or modified in last hour: {recent_orders}")
        
        # Show latest updates
        cursor.execute("""
            SELECT name, email, 
                   CASE WHEN updated_at > created_at THEN 'UPDATED' ELSE 'NEW' END as status,
                   updated_at
            FROM customers 
            WHERE updated_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
            ORDER BY updated_at DESC
            LIMIT 5
        """)
        
        print(f"\n🔄 Latest Customer Changes:")
        for name, email, status, updated_at in cursor.fetchall():
            print(f"  • {name} ({email}) - {status} at {updated_at}")
            
    except Exception as e:
        print(f"❌ Error showing recent changes: {e}")
    finally:
        cursor.close()

def main():
    """Main function"""
    if len(sys.argv) != 5:
        print("Usage: python3 simulate_incremental_data.py <rds_endpoint> <db_name> <username> <password>")
        print("Example: python3 simulate_incremental_data.py mydb.xxxxx.us-east-1.rds.amazonaws.com analytics_db analytics_user mypassword")
        sys.exit(1)
    
    endpoint = sys.argv[1]
    db_name = sys.argv[2]
    username = sys.argv[3]
    password = sys.argv[4]
    
    print(f"🔄 Simulating incremental data changes...")
    print(f"📍 Endpoint: {endpoint}")
    print(f"🗄️  Database: {db_name}")
    
    connection = connect_to_db(endpoint, db_name, username, password)
    
    if connection:
        try:
            # Add some new customers
            add_new_customers(connection, 3)
            
            # Update some existing customers
            update_existing_customers(connection, 2)
            
            # Add new orders
            add_new_orders(connection, 8)
            
            # Update some existing orders
            update_existing_orders(connection, 3)
            
            # Show summary
            show_recent_changes(connection)
            
            print(f"\n✅ Incremental data simulation completed!")
            print(f"💡 You can now run the Glue ETL jobs to test incremental processing:")
            print(f"   python3 run_glue_jobs.py run-all")
            
        finally:
            connection.close()
    else:
        print("❌ Failed to connect to database")
        sys.exit(1)

if __name__ == "__main__":
    main()
