import bcrypt
import mysql.connector
from mysql.connector import Error

def is_bcrypt_hash(password_hash):
    """Cek apakah string sudah merupakan hash bcrypt"""
    if not password_hash:
        return False
    
    # Cek semua prefix bcrypt yang mungkin
    bcrypt_prefixes = ['$2a$', '$2b$', '$2y$']
    return any(password_hash.startswith(prefix) for prefix in bcrypt_prefixes)

def hash_existing_passwords():
    """Hash password plaintext yang ada di database ke bcrypt"""
    
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='db_kasir1'
        )
        print("✓ Koneksi ke database berhasil")
        
    except Error as e:
        print(f"✗ Gagal koneksi database: {e}")
        return
    
    cursor = conn.cursor(dictionary=True)
    
    # 1. Ambil semua user
    cursor.execute("SELECT id, username, password_hash FROM users")
    users = cursor.fetchall()
    
    print(f"\n📊 Ditemukan {len(users)} user:")
    for user in users:
        print(f"  - ID: {user['id']}, Username: {user['username']}")
    
    update_cursor = conn.cursor()
    updated_count = 0
    skipped_count = 0
    
    # 2. Hash password yang masih plaintext
    for user in users:
        current_password = user['password_hash']
        
        # Skip jika password kosong
        if not current_password:
            print(f"  ⚠️ Password kosong untuk user '{user['username']}' - diabaikan")
            skipped_count += 1
            continue
        
        # Cek apakah sudah dihash
        if is_bcrypt_hash(current_password):
            print(f"  ✅ Password user '{user['username']}' sudah dihash (bcrypt)")
            skipped_count += 1
            continue
        
        try:
            # Hash password menggunakan bcrypt
            hashed = bcrypt.hashpw(current_password.encode('utf-8'), bcrypt.gensalt())
            hashed_str = hashed.decode('utf-8')
            
            # Update ke database
            update_cursor.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (hashed_str, user['id'])
            )
            updated_count += 1
            print(f"  🔐 Updated password for user '{user['username']}' (ID: {user['id']})")
            
        except Exception as e:
            print(f"  ✗ Gagal hash password untuk user '{user['username']}': {e}")
    
    # Commit perubahan
    conn.commit()
    
    # 3. Verifikasi hasil
    print(f"\n📊 HASIL AKHIR:")
    print(f"  ✅ Diupdate: {updated_count} password")
    print(f"  ⏭️  Dilewati: {skipped_count} password (sudah dihash)")
    print(f"  📋 Total: {len(users)} user")
    
    # Tampilkan hasil akhir
    print("\n📋 Status semua user:")
    cursor.execute("SELECT id, username, password_hash FROM users")
    final_users = cursor.fetchall()
    
    for user in final_users:
        hash_preview = user['password_hash'][:20] if user['password_hash'] else '[KOSONG]'
        if is_bcrypt_hash(user['password_hash']):
            status = "✅ HASHED"
        elif user['password_hash']:
            status = "⚠️ PLAINTEXT"
        else:
            status = "❌ KOSONG"
        print(f"  - {user['username']}: {status} ({hash_preview}...)")
    
    # Tutup koneksi
    cursor.close()
    update_cursor.close()
    conn.close()
    print("\n🔒 Database connection closed")

def create_admin_user():
    """Buat user admin dengan password yang sudah dihash"""
    
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='db_kasir1'
    )
    
    cursor = conn.cursor()
    
    # User admin
    users_to_create = [
        {
            'username': 'admin',
            'email': 'admin@justcani.com',
            'whatsapp': '+6281234567891',
            'password': 'admin123',
            'role': 'admin'
        },
        {
            'username': 'kasir1',
            'email': 'kasir@justcani.com',
            'whatsapp': '+6281234567890',
            'password': 'kasir123',
            'role': 'kasir'
        }
    ]
    
    created_count = 0
    
    for user_data in users_to_create:
        # Hash password
        hashed = bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt())
        
        # Cek apakah user sudah ada
        check_cursor = conn.cursor()
        check_cursor.execute("SELECT id FROM users WHERE username = %s", (user_data['username'],))
        
        if check_cursor.fetchone():
            print(f"  ⚠️ User '{user_data['username']}' sudah ada, dilewati")
            check_cursor.close()
            continue
        
        check_cursor.close()
        
        # Insert user baru
        sql = """
        INSERT INTO users (username, email, whatsapp, password_hash, role) 
        VALUES (%s, %s, %s, %s, %s)
        """
        
        values = (
            user_data['username'],
            user_data['email'],
            user_data['whatsapp'],
            hashed.decode('utf-8'),
            user_data['role']
        )
        
        try:
            cursor.execute(sql, values)
            created_count += 1
            print(f"  ✅ User '{user_data['username']}' berhasil dibuat (role: {user_data['role']})")
        except Error as e:
            print(f"  ✗ Gagal buat user '{user_data['username']}': {e}")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"\n✅ {created_count} user baru berhasil dibuat!")

def reset_user_password():
    """Reset password user tertentu"""
    
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='db_kasir1'
    )
    
    cursor = conn.cursor(dictionary=True)
    
    # Tampilkan semua user
    cursor.execute("SELECT id, username, role FROM users ORDER BY id")
    users = cursor.fetchall()
    
    print("\n📋 Daftar user:")
    for user in users:
        print(f"  [{user['id']}] {user['username']} ({user['role']})")
    
    try:
        user_id = int(input("\nMasukkan ID user yang ingin direset password: "))
        
        # Cari user
        target_user = None
        for user in users:
            if user['id'] == user_id:
                target_user = user
                break
        
        if not target_user:
            print("✗ User tidak ditemukan!")
            return
        
        new_password = input(f"Masukkan password baru untuk '{target_user['username']}': ").strip()
        
        if len(new_password) < 3:
            print("✗ Password terlalu pendek!")
            return
        
        # Hash password baru
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        
        update_cursor = conn.cursor()
        update_cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (hashed.decode('utf-8'), user_id)
        )
        
        conn.commit()
        update_cursor.close()
        
        print(f"✅ Password untuk '{target_user['username']}' berhasil direset!")
        
    except ValueError:
        print("✗ ID harus berupa angka!")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("🔐 PASSWORD MANAGEMENT UTILITY - JustCani")
    print("=" * 50)
    
    while True:
        print("\nPilih opsi:")
        print("1. Hash password existing (nabil & whitesvil)")
        print("2. Buat user admin & kasir baru")
        print("3. Reset password user tertentu")
        print("4. Lihat semua user")
        print("5. Keluar")
        
        choice = input("\nPilihan (1/2/3/4/5): ").strip()
        
        if choice == '1':
            hash_existing_passwords()
        elif choice == '2':
            create_admin_user()
        elif choice == '3':
            reset_user_password()
        elif choice == '4':
            conn = mysql.connector.connect(
                host='localhost',
                user='root',
                password='',
                database='db_kasir1'
            )
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, username, email, role, LEFT(password_hash, 30) as hash_preview FROM users")
            users = cursor.fetchall()
            
            print(f"\n📊 Total {len(users)} user:")
            for user in users:
                status = "🔐 HASHED" if user['hash_preview'] and user['hash_preview'].startswith('$2') else "⚠️ PLAIN"
                print(f"  [{user['id']}] {user['username']} ({user['role']}) - {user['email']}")
                print(f"     Hash: {user['hash_preview']}... - Status: {status}\n")
            
            cursor.close()
            conn.close()
        elif choice == '5':
            print("Keluar...")
            break
        else:
            print("Pilihan tidak valid!")