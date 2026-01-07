import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt
import traceback
import json
import random
import os
from datetime import datetime

# ============================================
# BARCODE IMPORTS
# ============================================
try:
    import barcode
    from barcode.writer import ImageWriter
    from io import BytesIO
    import base64
    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False
    print("INFO: python-barcode not installed. Barcode features limited.")
# ============================================

# Di logic.py atau Database class
import os
import psycopg2
from psycopg2.extras import RealDictCursor

class Database:
    @staticmethod
    def get_conn():
        try:
            # Debug info
            print(f"[DATABASE] Connecting to database...")
            
            # Gunakan DATABASE_URL dari environment Vercel
            db_url = os.environ.get('DATABASE_URL')
            
            if not db_url:
                print("[DATABASE] ⚠️ DATABASE_URL not found, using fallback")
                # Fallback untuk local development
                db_url = "postgresql://neondb_owner:npg_ptNaxkIwe4D9@ep-little-hat-ah5adtxh-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require"
            
            print(f"[DATABASE] URL: {db_url[:50]}...")
            
            # Connect dengan timeout
            conn = psycopg2.connect(
                db_url,
                connect_timeout=10,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5
            )
            
            print("[DATABASE] ✅ Connected successfully")
            return conn
            
        except Exception as e:
            print(f"[DATABASE] ❌ Connection failed: {e}")
            traceback.print_exc()
            return None

class Inventory:
    def __init__(self, db_conn):
        self.db = db_conn

    def search_produk(self, query=''):
        """Search produk biasa - FIXED FOR POSTGRESQL"""
        if not self.db: 
            print("[INVENTORY] No database connection")
            return []
        
        cursor = self.db.cursor(cursor_factory=RealDictCursor)
        try:
            # ✅ Gunakan kolom yang sesuai dengan database Neon/PostgreSQL Anda
            sql = """
            SELECT 
                no_sku as "no_SKU",
                name_product as "Name_product",
                price as "Price",
                expired_date,
                COALESCE(stok, 0) as stok,
                'biasa' as type
            FROM produk_biasa 
            WHERE name_product ILIKE %s 
            OR no_sku::TEXT ILIKE %s
            ORDER BY name_product
            LIMIT 50
            """
            
            search_pattern = f"%{query}%" if query else "%"
            cursor.execute(sql, (search_pattern, search_pattern))
            
            results = cursor.fetchall()
            
            print(f"[DEBUG] search_produk found {len(results)} results")
            
            # Konversi ke format yang diharapkan frontend
            formatted_results = []
            for r in results:
                item = {
                    'no_SKU': r['no_SKU'],
                    'Name_product': r['Name_product'],
                    'Price': float(r['Price']) if r['Price'] else 0,
                    'stok': int(r['stok']) if r['stok'] else 0,
                    'type': 'biasa'
                }
                
                if r['expired_date']:
                    if isinstance(r['expired_date'], str):
                        item['expired_date'] = r['expired_date']
                    else:
                        item['expired_date'] = r['expired_date'].isoformat() if hasattr(r['expired_date'], 'isoformat') else str(r['expired_date'])
                
                formatted_results.append(item)
            
            return formatted_results
            
        except Exception as e:
            print(f"[ERROR] search_produk failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            cursor.close()

    def search_produk_lelang(self, query=''):
        """Search produk lelang - FIXED VERSION"""
        print(f"[DEBUG] Searching produk lelang: '{query}'")
        
        if not self.db: 
            print("[DEBUG] No database connection")
            return []
        
        cursor = self.db.cursor(cursor_factory=RealDictCursor)
        try:
            # ✅ SIMPLE QUERY - Sesuai struktur database
            sql = """
            SELECT 
                no_sku,
                name_product,
                price,
                expired_date
            FROM produk_lelang 
            WHERE name_product ILIKE %s 
            OR CAST(no_sku AS VARCHAR) ILIKE %s
            ORDER BY name_product
            LIMIT 50
            """
            
            search_pattern = f"%{query}%" if query else "%"
            cursor.execute(sql, (search_pattern, search_pattern))
            
            results = cursor.fetchall()
            
            print(f"[DEBUG] Found {len(results)} lelang results")
            
            # Format hasil dengan field names yang konsisten
            formatted_results = []
            for r in results:
                formatted_results.append({
                    'no_SKU': r['no_sku'],  # Perhatikan: 'no_sku' bukan 'no_SKU'
                    'Name_product': r['name_product'],
                    'Price': r['price'],
                    'expired_date': r['expired_date'].isoformat() if r.get('expired_date') else None,
                    'type': 'lelang'
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"[ERROR] search_produk_lelang failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            cursor.close()
    def move_to_lelang(self, sku, reason):
        if not self.db: return False, "Database tidak terhubung"
        
        cursor = self.db.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("SELECT * FROM produk_biasa WHERE no_SKU = %s", (sku,))
            produk = cursor.fetchone()
            
            if not produk:
                return False, "Produk tidak ditemukan"
            
            harga_diskon = int(produk[3] * 0.5)
            
            cursor.execute("""
                INSERT INTO produk_lelang (no_SKU, Name_product, expired_date, Price) 
                VALUES (%s, %s, %s, %s)
            """, (sku, produk[1], produk[2], harga_diskon))
            
            cursor.execute("DELETE FROM produk_biasa WHERE no_SKU = %s", (sku,))
            
            self.db.commit()
            return True, f"Produk dipindah ke lelang. Harga baru: Rp{harga_diskon:,}"
            
        except psycopg2.Error as e:
            self.db.rollback()
            return False, f"Error: {str(e)}"
        finally:
            cursor.close()

    def add_produk_baru(self, sku, name, harga, expired_date):
        if not self.db: return
        cursor = self.db.cursor(cursor_factory=RealDictCursor)
        try:
            sql = "INSERT INTO produk_biasa (no_SKU, Name_product, Price, expired_date, stok) VALUES (%s, %s, %s, %s, 0)"
            cursor.execute(sql, (sku, name, harga, expired_date))
            
            barcode_img = self.generate_product_barcode(sku, name, harga)
            if barcode_img:
                print(f"✅ Barcode generated for SKU: {sku}")
            
            self.db.commit()
        except psycopg2.Error as e:
            print(f"Error tambah produk: {e}")
            self.db.rollback()
        finally:
            cursor.close()
            
    def generate_product_barcode(self, sku, name, price):
        """Generate barcode untuk produk"""
        try:
            if not BARCODE_AVAILABLE:
                return None
            
            code128 = barcode.get_barcode_class('code128')
            barcode_instance = code128(str(sku), writer=ImageWriter())
            
            buffer = BytesIO()
            barcode_instance.write(buffer)
            buffer.seek(0)
            
            barcode_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f"data:image/png;base64,{barcode_base64}"
            
        except Exception as e:
            print(f"Error generating barcode: {e}")
            return None
    
    def save_barcode_to_db(self, sku, barcode_data):
        """Save barcode image to database"""
        if not self.db: return False
        
        cursor = self.db.cursor(cursor_factory=RealDictCursor)
        try:
            # Try to update produk_biasa first
            cursor.execute("""
                UPDATE produk_biasa 
                SET barcode_image = %s 
                WHERE no_SKU = %s
            """, (barcode_data, sku))
            
            # If no rows affected, try produk_lelang
            if cursor.rowcount == 0:
                cursor.execute("""
                    UPDATE produk_lelang 
                    SET barcode_image = %s 
                    WHERE no_SKU = %s
                """, (barcode_data, sku))
            
            self.db.commit()
            return True
        except Exception as e:
            print(f"Error saving barcode to DB: {e}")
            self.db.rollback()
            return False
        finally:
            cursor.close()

class TransactionHistory:
    def __init__(self, db_conn):
        self.db = db_conn
    
    def save_transaction(self, transaction_data):
        """Menyimpan transaksi ke history"""
        print(f"[HISTORY] Saving transaction: {transaction_data['transaction_id']}")
        
        if not self.db: 
            print("[HISTORY] Database not connected")
            return False
        
        cursor = self.db.cursor(cursor_factory=RealDictCursor)
        try:
            sql = """
            INSERT INTO transaction_history 
            (transaction_id, user_id, username, total_amount, transaction_type, 
            payment_method, items_count, details)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            print(f"[HISTORY] Executing SQL with params:")
            print(f"  transaction_id: {transaction_data['transaction_id']}")
            print(f"  user_id: {transaction_data['user_id']}")
            print(f"  username: {transaction_data['username']}")
            print(f"  total_amount: {transaction_data['total_amount']}")
            print(f"  transaction_type: {transaction_data['transaction_type']}")
            print(f"  payment_method: {transaction_data.get('payment_method', 'cash')}")
            print(f"  items_count: {transaction_data['items_count']}")
            print(f"  details: {transaction_data['details'][:100]}...")
            
            cursor.execute(sql, (
                transaction_data['transaction_id'],
                transaction_data['user_id'],
                transaction_data['username'],
                transaction_data['total_amount'],
                transaction_data['transaction_type'],
                transaction_data.get('payment_method', 'cash'),
                transaction_data['items_count'],
                transaction_data['details']
            ))
            
            print(f"[HISTORY] Insert successful, rows affected: {cursor.rowcount}")
            
            self.db.commit()
            print("[HISTORY] Commit successful")
            return True
        except psycopg2.Error as e:
            print(f"[HISTORY] Database error: {e}")
            print(f"[HISTORY] Error details: {e.pgerror if hasattr(e, 'pgerror') else 'N/A'}")
            self.db.rollback()
            return False
        except Exception as e:
            print(f"[HISTORY] General error: {e}")
            import traceback
            print(f"[HISTORY] Traceback: {traceback.format_exc()}")
            self.db.rollback()
            return False
        finally:
            cursor.close()
            print("[HISTORY] Cursor closed")
    
    def get_all_transactions(self, limit=100, offset=0):
        """Mengambil semua transaksi"""
        if not self.db: return []
        
        cursor = self.db.cursor(cursor_factory=RealDictCursor)
        try:
            sql = """
            SELECT * FROM transaction_history 
            ORDER BY transaction_date DESC 
            LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (limit, offset))
            return cursor.fetchall()
        except psycopg2.Error as e:
            print(f"Error get transactions: {e}")
            return []
        finally:
            cursor.close()
    
    def get_transactions_by_date(self, start_date, end_date):
        """Mengambil transaksi berdasarkan rentang tanggal"""
        if not self.db: return []
        
        cursor = self.db.cursor(cursor_factory=RealDictCursor)
        try:
            sql = """
            SELECT * FROM transaction_history 
            WHERE DATE(transaction_date) BETWEEN %s AND %s
            ORDER BY transaction_date DESC
            """
            cursor.execute(sql, (start_date, end_date))
            return cursor.fetchall()
        except psycopg2.Error as e:
            print(f"Error get transactions by date: {e}")
            return []
        finally:
            cursor.close()
    
    def get_daily_summary(self, date):
        """Ringkasan transaksi harian"""
        if not self.db: return None
        
        cursor = self.db.cursor(cursor_factory=RealDictCursor)
        try:
            sql = """
            SELECT 
                COUNT(*) as total_transactions,
                SUM(total_amount) as total_revenue,
                SUM(CASE WHEN transaction_type = 'biasa' THEN 1 ELSE 0 END) as normal_count,
                SUM(CASE WHEN transaction_type = 'lelang' THEN 1 ELSE 0 END) as auction_count,
                MIN(transaction_date) as first_transaction,
                MAX(transaction_date) as last_transaction
            FROM transaction_history 
            WHERE DATE(transaction_date) = %s
            """
            cursor.execute(sql, (date,))
            return cursor.fetchone()
        except psycopg2.Error as e:
            print(f"Error get daily summary: {e}")
            return None
        finally:
            cursor.close()
    
    def get_monthly_report(self, year, month):
        """Laporan transaksi bulanan"""
        if not self.db: return []
        
        cursor = self.db.cursor(cursor_factory=RealDictCursor)
        try:
            sql = """
            SELECT 
                DATE(transaction_date) as date,
                COUNT(*) as transaction_count,
                SUM(total_amount) as daily_total,
                GROUP_CONCAT(DISTINCT username) as cashiers
            FROM transaction_history 
            WHERE YEAR(transaction_date) = %s AND MONTH(transaction_date) = %s
            GROUP BY DATE(transaction_date)
            ORDER BY date DESC
            """
            cursor.execute(sql, (year, month))
            return cursor.fetchall()
        except psycopg2.Error as e:
            print(f"Error get monthly report: {e}")
            return []
        finally:
            cursor.close()

class Transaction:
    def __init__(self, db_conn):
        self.db = db_conn
        self.history = TransactionHistory(db_conn)
    
    def generate_transaction_id(self):
        """Generate unique transaction ID"""
        timestamp = datetime.now().strftime("%y%m%d")
        random_num = random.randint(1000, 9999)
        return f"TRX-{timestamp}-{random_num}"
    
    def checkout(self, items, user_id, username):
        """Checkout transaksi biasa - FIXED FOR YOUR DATABASE STRUCTURE"""
        print(f"🎯 [CHECKOUT] User: {username}, Items: {len(items)}")
        
        if not self.db:
            return False, "Database tidak terhubung"
        
        cursor = self.db.cursor()
        
        try:
            total = 0
            transaction_items = []
            
            # VALIDATE AND CALCULATE
            for item in items:
                sku = str(item.get('sku', '')).strip()
                qty = int(item.get('qty', 1))
                
                # Get product
                cursor.execute("""
                    SELECT name_product, price, stok 
                    FROM produk_biasa 
                    WHERE no_sku = %s
                """, (sku,))
                
                product = cursor.fetchone()
                if not product:
                    return False, f"Produk SKU {sku} tidak ditemukan"
                
                name, price, stock = product
                
                if stock < qty:
                    return False, f"Stok {name} tidak cukup. Tersedia: {stock}"
                
                subtotal = price * qty
                total += subtotal
                
                transaction_items.append({
                    'sku': sku,
                    'name': name,
                    'price': float(price),
                    'qty': qty,
                    'subtotal': float(subtotal)
                })
                
                # Update stock
                cursor.execute(
                    "UPDATE produk_biasa SET stok = stok - %s WHERE no_sku = %s",
                    (qty, sku)
                )
            
            if total == 0:
                return False, "Total transaksi nol"
            
            # ✅ FIX: INSERT SESUAI STRUKTUR DATABASE ANDA
            import json
            from datetime import datetime
            
            transaction_id = f"TRX{datetime.now().strftime('%Y%m%d%H%M%S')}"  # Max 20 chars
            
            # Generate ID manually (karena bukan SERIAL)
            cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM transaction_history")
            next_id = cursor.fetchone()[0]
            
            # ✅ INSERT dengan struktur yang sesuai database
            cursor.execute("""
                INSERT INTO transaction_history 
                (id, transaction_id, transaction_date, user_id, username, 
                total_amount, transaction_type, payment_method, items_count, details)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                next_id,                     # id (manual)
                transaction_id,              # transaction_id (max 20 chars)
                datetime.now(),              # transaction_date
                user_id,                     # user_id
                username,                    # username
                total,                       # total_amount
                'biasa',                     # transaction_type
                'cash',                      # payment_method
                len(items),                  # items_count
                json.dumps(transaction_items, ensure_ascii=False)  # details
            ))
            
            self.db.commit()
            
            print(f"✅ [CHECKOUT SUCCESS] ID: {next_id}, TRX: {transaction_id}, Total: Rp{total:,.0f}")
            return True, f"Transaksi {transaction_id} berhasil! Total: Rp{total:,.0f}"
            
        except Exception as e:
            print(f"❌ [CHECKOUT ERROR] {e}")
            import traceback
            traceback.print_exc()
            
            if self.db:
                self.db.rollback()
            
            return False, f"Error: {str(e)}"
        finally:
            cursor.close()
class CashierSystem:
    def __init__(self):
        print("[CASHIERSYSTEM] Initializing...")
        self.db = Database.get_conn()
        if self.db:
            self.inventory = Inventory(self.db)
            self.transaction = Transaction(self.db)
            print("[CASHIERSYSTEM] ✅ Initialized successfully")
        else:
            print("[CASHIERSYSTEM] ❌ Failed to initialize")
            self.inventory = None
            self.transaction = None
    
    @staticmethod
    def hash_password(password):
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def check_password(hashed_password, password):
        try:
            if hashed_password is None:
                return False
                
            # Jika hashed_password adalah string, encode ke bytes
            if isinstance(hashed_password, str):
                hashed_bytes = hashed_password.encode('utf-8')
            else:
                hashed_bytes = hashed_password
            
            return bcrypt.checkpw(password.encode('utf-8'), hashed_bytes)
        except Exception as e:
            print(f"[CHECK_PASSWORD ERROR] {e}")
            return False

    def login_user(self, email_or_username, password):
        """Login dengan email ATAU username - FIXED FOR VERCELL"""
        print(f"[LOGIN] Attempting login for: {email_or_username}")
        
        if not self.db: 
            print("[LOGIN] ❌ No database connection")
            return None
            
        cursor = self.db.cursor(cursor_factory=RealDictCursor)
        try:
            sql = """
            SELECT id, username, email, password_hash, role, profile_pic
            FROM users 
            WHERE email = %s OR username = %s
            LIMIT 1
            """
            
            print(f"[LOGIN] Executing query: {sql}")
            cursor.execute(sql, (email_or_username, email_or_username))
            user = cursor.fetchone()
            
            if user:
                print(f"[LOGIN] User found: {user['username']}")
                print(f"[LOGIN] Hashed password type: {type(user['password_hash'])}")
                print(f"[LOGIN] Hashed password sample: {str(user['password_hash'])[:50] if user['password_hash'] else 'NULL'}")
                
                # Check password
                is_password_correct = self.check_password(user['password_hash'], password)
                print(f"[LOGIN] Password check result: {is_password_correct}")
                
                if is_password_correct:
                    print(f"[LOGIN] ✅ Login successful for {user['username']}")
                    return {
                        'id': user['id'],
                        'username': user['username'],
                        'email': user['email'],
                        'role': user['role'],
                        'profile_pic': user['profile_pic'] or '/static/img/default-avatar.png'
                    }
                else:
                    print(f"[LOGIN] ❌ Password incorrect")
            else:
                print(f"[LOGIN] ❌ User not found")
                
            return None
            
        except psycopg2.Error as e:
            print(f"[LOGIN ERROR] Database error: {e}")
            print(f"Error details: {e.pgerror if hasattr(e, 'pgerror') else 'N/A'}")
            return None
        except Exception as e:
            print(f"[LOGIN ERROR] General error: {e}")
            traceback.print_exc()
            return None
        finally:
            cursor.close()
            print("[LOGIN] Cursor closed")

    def close(self):
        if self.db: self.db.close()