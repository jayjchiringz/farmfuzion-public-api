import os
from sqlalchemy import create_engine, text, inspect
import uuid

# ============================================
# Your Neon Database Configuration
# ============================================
DATABASE_URL = "postgresql://neondb_owner:npg_ydktDfeI8h6K@ep-odd-shadow-a8hbxcs0-pooler.eastus2.azure.neon.tech:5432/neondb?sslmode=require"
SCHEMA_NAME = "public_marketplace"

print("=" * 60)
print("🚀 FarmFuzion Public API - Database Setup")
print("=" * 60)
print(f"📊 Database: Neon PostgreSQL")
print(f"📊 Host: ep-odd-shadow-a8hbxcs0-pooler.eastus2.azure.neon.tech")
print(f"📊 Schema: {SCHEMA_NAME}")
print("=" * 60)

def setup_database():
    try:
        # Create engine with SSL
        engine = create_engine(
            DATABASE_URL,
            connect_args={
                'sslmode': 'require'
            }
        )
        
        # Test connection
        with engine.connect() as conn:
            print("✅ Database connection successful")
            
            # Create schema
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME}'))
            conn.commit()
            print(f"✅ Schema '{SCHEMA_NAME}' created/verified")
            
            # Create the marketplace_products table
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.marketplace_products (
                id VARCHAR PRIMARY KEY,
                product_name VARCHAR NOT NULL,
                category VARCHAR,
                quantity FLOAT DEFAULT 0,
                unit VARCHAR DEFAULT 'kg',
                price_per_unit FLOAT DEFAULT 0,
                available BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            conn.execute(text(create_table_sql))
            conn.commit()
            print("✅ Table 'marketplace_products' created/verified")
            
            # Check if table exists
            inspector = inspect(engine)
            tables = inspector.get_table_names(schema=SCHEMA_NAME)
            print(f"📊 Tables in schema '{SCHEMA_NAME}': {tables}")
            
            # Insert sample products for testing
            sample_products = [
                {
                    "id": str(uuid.uuid4()),
                    "name": "Fresh Tomatoes",
                    "category": "Vegetables",
                    "quantity": 500,
                    "unit": "kg",
                    "price": 120.0
                },
                {
                    "id": str(uuid.uuid4()),
                    "name": "Organic Potatoes",
                    "category": "Vegetables",
                    "quantity": 1000,
                    "unit": "kg",
                    "price": 80.0
                },
                {
                    "id": str(uuid.uuid4()),
                    "name": "Green Beans",
                    "category": "Vegetables",
                    "quantity": 300,
                    "unit": "kg",
                    "price": 150.0
                },
                {
                    "id": str(uuid.uuid4()),
                    "name": "Mangoes",
                    "category": "Fruits",
                    "quantity": 200,
                    "unit": "kg",
                    "price": 200.0
                },
                {
                    "id": str(uuid.uuid4()),
                    "name": "Avocados",
                    "category": "Fruits",
                    "quantity": 150,
                    "unit": "kg",
                    "price": 250.0
                }
            ]
            
            for product in sample_products:
                insert_sql = f"""
                INSERT INTO {SCHEMA_NAME}.marketplace_products 
                (id, product_name, category, quantity, unit, price_per_unit, available, created_at)
                VALUES 
                ('{product['id']}', '{product['name']}', '{product['category']}', 
                 {product['quantity']}, '{product['unit']}', {product['price']}, 
                 true, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO NOTHING
                """
                conn.execute(text(insert_sql))
            
            conn.commit()
            print(f"✅ {len(sample_products)} sample products inserted")
            
            # Count products
            count_sql = f"SELECT COUNT(*) FROM {SCHEMA_NAME}.marketplace_products"
            result = conn.execute(text(count_sql))
            count = result.scalar()
            print(f"📊 Total products in database: {count}")
            
            print("\n" + "=" * 60)
            print("🎉 Database setup complete!")
            print("=" * 60)
            print("\n📋 Next steps:")
            print("1. Update DATABASE_URL in Render environment")
            print("2. Deploy the public API")
            print("3. Test endpoints:")
            print("   - GET  /api/v1/products")
            print("   - GET  /api/v1/products/{id}")
            print("   - POST /api/v1/products (with API key)")
            print("=" * 60)
            
            return True
            
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

if __name__ == "__main__":
    setup_database()