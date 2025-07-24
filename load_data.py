#!/usr/bin/env python3
"""
Script to load sample data into PostgreSQL RDS instance
Run this after the infrastructure is deployed
"""

import psycopg2
import sys
import os
from datetime import datetime, timedelta
import random

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
        print(f"Successfully connected to database: {db_name}")
        return connection
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def create_tables(connection):
    """Create tables and load sample data"""
    cursor = connection.cursor()
    
    try:
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
        
        print("Tables created successfully")
        
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
            ('Ivan Rodriguez', 'ivan.rodriguez@email.com'),
            ('Julia Lee', 'julia.lee@email.com'),
            ('Kevin Park', 'kevin.park@email.com'),
            ('Linda Thompson', 'linda.thompson@email.com'),
            ('Mike White', 'mike.white@email.com')
        ]
        
        # Insert customers
        for name, email in customers:
            cursor.execute("""
                INSERT INTO customers (name, email) VALUES (%s, %s)
                ON CONFLICT (email) DO NOTHING
            """, (name, email))
        
        print(f"Inserted {len(customers)} customers")
        
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
            ('Bluetooth Speaker', 79.99),
            ('Gaming Chair', 249.99),
            ('Webcam HD', 89.99),
            ('External Hard Drive', 129.99),
            ('Portable Charger', 39.99),
            ('Wireless Earbuds', 179.99),
            ('Laptop Stand', 59.99),
            ('Cable Management', 24.99),
            ('Blue Light Glasses', 49.99),
            ('Desk Lamp LED', 69.99)
        ]
        
        # Generate sample orders for the last 30 days
        order_count = 0
        for days_ago in range(30):
            order_date = datetime.now().date() - timedelta(days=days_ago)
            
            # Random number of orders per day (1-8)
            daily_orders = random.randint(1, 8)
            
            for _ in range(daily_orders):
                customer_id = random.randint(1, len(customers))
                product_name, base_price = random.choice(products)
                quantity = random.randint(1, 3)
                # Add some price variation (±10%)
                price_variation = random.uniform(0.9, 1.1)
                price = round(base_price * price_variation, 2)
                
                cursor.execute("""
                    INSERT INTO orders (customer_id, product_name, quantity, price, order_date)
                    VALUES (%s, %s, %s, %s, %s)
                """, (customer_id, product_name, quantity, price, order_date))
                
                order_count += 1
        
        print(f"Inserted {order_count} orders")
        
        connection.commit()
        print("Sample data loaded successfully!")
        
        # Display some statistics
        cursor.execute("SELECT COUNT(*) FROM customers")
        customer_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM orders")
        order_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(quantity * price) FROM orders")
        total_revenue = cursor.fetchone()[0]
        
        print(f"\nDatabase Statistics:")
        print(f"Total Customers: {customer_count}")
        print(f"Total Orders: {order_count}")
        print(f"Total Revenue: ${total_revenue:.2f}")
        
    except Exception as e:
        print(f"Error creating tables and data: {e}")
        connection.rollback()
    finally:
        cursor.close()

def main():
    """Main function"""
    if len(sys.argv) != 5:
        print("Usage: python load_data.py <rds_endpoint> <db_name> <username> <password>")
        print("Example: python load_data.py mydb.xxxxx.us-east-1.rds.amazonaws.com analytics_db analytics_user mypassword")
        sys.exit(1)
    
    endpoint = sys.argv[1]
    db_name = sys.argv[2]
    username = sys.argv[3]
    password = sys.argv[4]
    
    print(f"Connecting to RDS endpoint: {endpoint}")
    print(f"Database: {db_name}")
    print(f"Username: {username}")
    
    connection = connect_to_db(endpoint, db_name, username, password)
    
    if connection:
        create_tables(connection)
        connection.close()
        print("Connection closed")
    else:
        print("Failed to connect to database")
        sys.exit(1)

if __name__ == "__main__":
    main()