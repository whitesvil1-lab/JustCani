# creates_tables.py - SIMPLE VERSION
import psycopg2
import os

def create_tables():
    print("🔧 Creating database tables...")
    
    try:
        # Ganti dengan URL database Anda
        db_url = "postgresql://neondb_owner:npg_ptNaxkIwe4D9@ep-little-hat-ah5adtxh-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require"
        
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Buat tabel transaction_history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transaction_history (
                id SERIAL PRIMARY KEY,
                transaction_id VARCHAR(50) UNIQUE,
                user_id INTEGER,
                username VARCHAR(100),
                total_amount DECIMAL(10,2),
                transaction_type VARCHAR(20),
                payment_method VARCHAR(20) DEFAULT 'cash',
                items_count INTEGER,
                details TEXT,
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tambah kolom barcode jika belum ada
        cursor.execute("""
            ALTER TABLE produk_biasa 
            ADD COLUMN IF NOT EXISTS barcode_image TEXT
        """)
        
        cursor.execute("""
            ALTER TABLE produk_lelang 
            ADD COLUMN IF NOT EXISTS barcode_image TEXT
        """)
        
        conn.commit()
        print("✅ Tables created successfully!")
        
        # Cek tabel
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = cursor.fetchall()
        print(f"📊 Tables found: {[t[0] for t in tables]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    create_tables()
