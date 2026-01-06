import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor

# LINK DATABASE VERCEL KAMU
DB_URL = "postgresql://neondb_owner:npg_ptNaxkIwe4D9@ep-little-hat-ah5adtxh-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require"

def is_bcrypt_hash(password_hash):
    if not password_hash: return False
    bcrypt_prefixes = ['$2a$', '$2b$', '$2y$']
    return any(password_hash.startswith(prefix) for prefix in bcrypt_prefixes)

def hash_existing_passwords():
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, username, password_hash FROM users")
        users = cursor.fetchall()
        
        update_cursor = conn.cursor()
        for user in users:
            if not user['password_hash'] or is_bcrypt_hash(user['password_hash']):
                continue
            hashed = bcrypt.hashpw(user['password_hash'].encode('utf-8'), bcrypt.gensalt())
            update_cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (hashed.decode('utf-8'), user['id']))
        
        conn.commit()
        print("✓ Berhasil update password lama!")
        conn.close()
    except Exception as e:
        print(f"✗ Error: {e}")

def create_admin_user():
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        users_to_create = [
            {'username': 'admin', 'email': 'admin@justcani.com', 'pw': 'admin123', 'role': 'admin'},
            {'username': 'kasir1', 'email': 'kasir@justcani.com', 'pw': 'kasir123', 'role': 'kasir'}
        ]
        for u in users_to_create:
            hashed = bcrypt.hashpw(u['pw'].encode('utf-8'), bcrypt.gensalt())
            cursor.execute("INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s) ON CONFLICT (username) DO NOTHING", 
                           (u['username'], u['email'], hashed.decode('utf-8'), u['role']))
        conn.commit()
        print("✓ User admin/kasir siap digunakan!")
        conn.close()
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    print("🔐 DATABASE MANAGEMENT - JustCani")
    print("1. Hash password lama\n2. Buat user admin/kasir baru\n3. Lihat semua user\n4. Keluar")
    choice = input("Pilihan: ")
    if choice == '1': hash_existing_passwords()
    elif choice == '2': create_admin_user()
    elif choice == '3':
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, username, role, email FROM users")
        for u in cur.fetchall(): print(u)
        conn.close()