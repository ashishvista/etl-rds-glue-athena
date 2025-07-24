#!/usr/bin/env python3
"""
Quick data loading script
"""

import psycopg2
from datetime import datetime, timedelta
import random

def main():
    try:
        print("🔗 Connecting to database...")
        conn = psycopg2.connect(
            host='data-analytics-postgres-v2.ccbsg6ya6wfa.us-east-1.rds.amazonaws.com',
            port=5432,
            database='analytics_db',
            user='analytics_user',
            password='ChangeMe123!'
        )
        print("✅ Connected successfully!")
        
        cursor = conn.cursor()
        
        print("📋 Creating tables...")
        
        # Create function for updating timestamps
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)
        
        # Create customers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            DROP TRIGGER IF EXISTS update_customers_updated_at ON customers;
            CREATE TRIGGER update_customers_updated_at
                BEFORE UPDATE ON customers
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """)
        
        # Create orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id SERIAL PRIMARY KEY,
                customer_id INTEGER REFERENCES customers(customer_id),
                product_name VARCHAR(100) NOT NULL,
                quantity INTEGER NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                order_date DATE DEFAULT CURRENT_DATE,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            DROP TRIGGER IF EXISTS update_orders_updated_at ON orders;
            CREATE TRIGGER update_orders_updated_at
                BEFORE UPDATE ON orders
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """)
        
        print("✅ Tables created!")
        
        # Clear existing data
        cursor.execute("DELETE FROM orders")
        cursor.execute("DELETE FROM customers")
        cursor.execute("ALTER SEQUENCE customers_customer_id_seq RESTART WITH 1")
        cursor.execute("ALTER SEQUENCE orders_order_id_seq RESTART WITH 1")
        
        print("🧹 Cleared existing data")
        
        # Sample customer data
        customers = [
            ('John Doe', 'john.doe@email.com'),
            ('Jane Smith', 'jane.smith@email.com'),
            ('Bob Johnson', 'bob.johnson@email.com'),
            ('Alice Brown', 'alice.brown@email.com'),
            ('Charlie Wilson', 'charlie.wilson@email.com'),
            ('Diana Martinez', 'diana.martinez@email.com'),
            ('Erik Anderson', 'erik.anderson@email.com'),
            ('Fiona Taylor', 'fiona.taylor@email.com'),
            ('George Davis', 'george.davis@email.com'),
            ('Helen Garcia', 'helen.garcia@email.com'),
        ]
        
        print("👥 Inserting customers...")
        for name, email in customers:
            cursor.execute("""
                INSERT INTO customers (name, email) VALUES (%s, %s)
            """, (name, email))
        
        print(f"✅ Inserted {len(customers)} customers")
        
        # Sample products with prices
        products = [
            ('Laptop Pro', 1299.99),
            ('Smartphone X', 899.99),
            ('Tablet Air', 599.99),
            ('Wireless Mouse', 29.99),
            ('Mechanical Keyboard', 149.99),
            ('4K Monitor', 499.99),
            ('Wireless Headphones', 299.99),
            ('Smart Watch', 399.99),
            ('Phone Case', 19.99),
            ('USB Cable', 12.99),
        ]
        
        print("🛒 Inserting orders...")
        order_count = 0
        for days_ago in range(7):  # Last 7 days
            order_date = datetime.now().date() - timedelta(days=days_ago)
            
            # Random number of orders per day (2-5)
            daily_orders = random.randint(2, 5)
            
            for _ in range(daily_orders):
                customer_id = random.randint(1, len(customers))
                product_name, base_price = random.choice(products)
                quantity = random.randint(1, 3)
                price = round(base_price, 2)
                
                cursor.execute("""
                    INSERT INTO orders (customer_id, product_name, quantity, price, order_date)
                    VALUES (%s, %s, %s, %s, %s)
                """, (customer_id, product_name, quantity, price, order_date))
                
                order_count += 1
        
        print(f"✅ Inserted {order_count} orders")
        
        conn.commit()
        
        # Display statistics
        cursor.execute("SELECT COUNT(*) FROM customers")
        customer_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders")
        total_orders = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(quantity * price) FROM orders")
        total_revenue = cursor.fetchone()[0]
        
        print(f"\n📊 Database Statistics:")
        print(f"   👥 Total Customers: {customer_count}")
        print(f"   🛒 Total Orders: {total_orders}")
        print(f"   💰 Total Revenue: ${total_revenue:.2f}")
        
        cursor.close()
        conn.close()
        print("\n🎉 Data loading completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
