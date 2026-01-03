import mysql.connector
from mysql.connector import Error
import bcrypt
import json
import random
from datetime import datetime

# ============================================
# BARCODE IMPORTS (tambah di atas)
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

class Database:
    @staticmethod
    def get_conn():
        try:
            return mysql.connector.connect(
                host='localhost',
                user='root',
                password='',
                database='db_kasir1'
            )
        except Error as e:
            print(f"Gagal koneksi database: {e}")
            return None

class Inventory:
    def __init__(self, db_conn):
        self.db = db_conn

    # ============================================
    # FUNGSI BARCODE (TAMBAH DI DALAM CLASS)
    # ============================================
    
    def generate_product_barcode(self, sku, product_name, price):
        """Generate barcode image untuk produk baru"""
        if not BARCODE_AVAILABLE:
            return None
        
        try:
            # Generate barcode Code128
            code128 = barcode.get_barcode_class('code128')
            barcode_instance = code128(str(sku), writer=ImageWriter())
            
            # Save to bytes
            buffer = BytesIO()
            barcode_instance.write(buffer)
            buffer.seek(0)
            
            # Convert to base64
            barcode_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            barcode_data = f"data:image/png;base64,{barcode_base64}"
            
            # Save to database
            cursor = self.db.cursor()
            try:
                # Try regular products          
                cursor.execute("""
                    UPDATE produk_biasa 
                    SET barcode_image = %s 
                    WHERE no_SKU = %s
                """, (barcode_data, sku))
                
                # Try auction products
                cursor.execute("""
                    UPDATE produk_lelang 
                    SET barcode_image = %s 
                    WHERE no_SKU = %s
                """, (barcode_data, sku))
                
                self.db.commit()
                print(f"✅ Barcode saved for SKU: {sku}")
            except Exception as e:
                print(f"⚠️ Could not save barcode to DB: {e}")
                self.db.rollback()
            finally:
                cursor.close()
            
            return barcode_data
        except Exception as e:
            print(f"Error generating barcode: {e}")
            return None
        
        def save_barcode_to_db(self, sku, barcode_data):
            """Simpan barcode ke database"""
            if not self.db:
                return False
        
            cursor = self.db.cursor()
            try:
                # Coba update produk biasa
                cursor.execute("""
                    UPDATE produk_biasa 
                    SET barcode_image = %s 
                    WHERE no_SKU = %s
                """, (barcode_data, sku))
            
                # Coba update produk lelang
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

def get_product_barcode(self, sku):
    """Ambil barcode dari database"""
    if not self.db:
        return None
    
    cursor = self.db.cursor(dictionary=True)
    try:
        # Cek di produk biasa
        cursor.execute("""
            SELECT barcode_image 
            FROM produk_biasa 
            WHERE no_SKU = %s
        """, (sku,))
        result = cursor.fetchone()
        
        if result and result['barcode_image']:
            return result['barcode_image']
        
        # Cek di produk lelang
        cursor.execute("""
            SELECT barcode_image 
            FROM produk_lelang 
            WHERE no_SKU = %s
        """, (sku,))
        result = cursor.fetchone()
        
        if result and result['barcode_image']:
            return result['barcode_image']
        
        return None
    except Exception as e:
        print(f"Error getting barcode from DB: {e}")
        return None
    finally:
        cursor.close()
    # ============================================
    
class Inventory:
    def __init__(self, db_conn):
        self.db = db_conn

    def search_produk(self, query):
        """Search produk biasa - FIXED"""
        if not self.db: 
            return []
        
        cursor = self.db.cursor(dictionary=True)
        try:
            # Clean query
            query = str(query).strip()
            
            # Jika query kosong, tampilkan semua
            if query == '':
                sql = "SELECT no_SKU, Name_product, Price, expired_date, stok FROM produk_biasa LIMIT 50"
                cursor.execute(sql)
            else:
                # Cari dengan berbagai cara
                sql = """
                SELECT no_SKU, Name_product, Price, expired_date, stok 
                FROM produk_biasa 
                WHERE Name_product LIKE %s 
                OR no_SKU = %s
                OR CAST(no_SKU AS CHAR) = %s
                LIMIT 50
                """
                
                # Coba convert ke integer untuk exact match
                try:
                    sku_int = int(query)
                except:
                    sku_int = -9999  # nilai yang tidak mungkin ada
                    
                cursor.execute(sql, (
                    f"%{query}%",      # Nama produk
                    sku_int,           # SKU sebagai integer
                    query              # SKU sebagai string
                ))
            
            result = cursor.fetchall()
            print(f"[DEBUG] search_produk found {len(result)} results for query: '{query}'")
            return result
            
        except Exception as e:
            print(f"[ERROR] search_produk: {e}")
            return []
        finally:
            cursor.close()

    def search_produk_lelang(self, query):
        """Search produk lelang - FIXED VERSION"""
        if not self.db: 
            return []
        
        cursor = self.db.cursor(dictionary=True)
        try:
            # FIX: Convert SKU to string untuk match dengan query
            sql = """
            SELECT no_SKU, Name_product, Price, expired_date 
            FROM produk_lelang 
            WHERE Name_product LIKE %s 
               OR no_SKU = %s 
               OR CAST(no_SKU AS CHAR) LIKE %s
            LIMIT 50
            """
            # Coba match dengan integer jika query adalah angka
            try:
                sku_int = int(query)
            except:
                sku_int = 0
                
            cursor.execute(sql, (f"%{query}%", sku_int, f"%{query}%"))
            result = cursor.fetchall()
            return result
        except Exception as e:
            print(f"[ERROR] search_produk_lelang: {e}")
            return []
        finally:
            cursor.close()

    def move_to_lelang(self, sku, reason):
        if not self.db: return False, "Database tidak terhubung"
        
        cursor = self.db.cursor()
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
            
        except Error as e:
            self.db.rollback()
            return False, f"Error: {str(e)}"
        finally:
            cursor.close()

    def add_produk_baru(self, sku, name, harga, expired_date):
        if not self.db: return
        cursor = self.db.cursor()
        try:
            sql = "INSERT INTO produk_biasa (no_SKU, Name_product, Price, expired_date, stok) VALUES (%s, %s, %s, %s, 0)"
            cursor.execute(sql, (sku, name, harga, expired_date))
            
            # ============================================
            # AUTO GENERATE BARCODE SETELAH TAMBAH PRODUK
            # ============================================
            barcode_img = self.generate_product_barcode(sku, name, harga)
            if barcode_img:
                print(f"✅ Barcode generated for SKU: {sku}")
            # ============================================
            
            self.db.commit()
        except Error as e:
            print(f"Error tambah produk: {e}")
            self.db.rollback()
        finally:
            cursor.close()
            
class TransactionHistory:
    def __init__(self, db_conn):
        self.db = db_conn
    
    def save_transaction(self, transaction_data):
        """Menyimpan transaksi ke history"""
        if not self.db: return False
        
        cursor = self.db.cursor()
        try:
            sql = """
            INSERT INTO transaction_history 
            (transaction_id, user_id, username, total_amount, transaction_type, 
             payment_method, items_count, details)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
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
            
            self.db.commit()
            return True
        except Error as e:
            print(f"Error save transaction: {e}")
            self.db.rollback()
            return False
        finally:
            cursor.close()
    
    def get_all_transactions(self, limit=100, offset=0):
        """Mengambil semua transaksi"""
        if not self.db: return []
        
        cursor = self.db.cursor(dictionary=True)
        try:
            sql = """
            SELECT * FROM transaction_history 
            ORDER BY transaction_date DESC 
            LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (limit, offset))
            return cursor.fetchall()
        except Error as e:
            print(f"Error get transactions: {e}")
            return []
        finally:
            cursor.close()
    
    def get_transactions_by_date(self, start_date, end_date):
        """Mengambil transaksi berdasarkan rentang tanggal"""
        if not self.db: return []
        
        cursor = self.db.cursor(dictionary=True)
        try:
            sql = """
            SELECT * FROM transaction_history 
            WHERE DATE(transaction_date) BETWEEN %s AND %s
            ORDER BY transaction_date DESC
            """
            cursor.execute(sql, (start_date, end_date))
            return cursor.fetchall()
        except Error as e:
            print(f"Error get transactions by date: {e}")
            return []
        finally:
            cursor.close()
    
    def get_daily_summary(self, date):
        """Ringkasan transaksi harian"""
        if not self.db: return None
        
        cursor = self.db.cursor(dictionary=True)
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
        except Error as e:
            print(f"Error get daily summary: {e}")
            return None
        finally:
            cursor.close()
    
    def get_monthly_report(self, year, month):
        """Laporan transaksi bulanan"""
        if not self.db: return []
        
        cursor = self.db.cursor(dictionary=True)
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
        except Error as e:
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
        """Checkout transaksi biasa dengan menyimpan history"""
        if not self.db: 
            return False, "Database tidak terhubung"
        
        cursor = self.db.cursor()
        try:
            total_amount = 0
            transaction_items = []
            
            # 1. Validasi dan hitung total
            for item in items:
                # Convert SKU to string for consistency
                sku = str(item['sku'])
                
                cursor.execute("SELECT Name_product, Price, stok FROM produk_biasa WHERE no_SKU = %s", (sku,))
                result = cursor.fetchone()
                
                if not result:
                    return False, f"Produk {sku} tidak ditemukan"
                
                if result[2] < item['qty']:
                    return False, f"Stok tidak cukup untuk {result[0]}"
                
                item_total = result[1] * item['qty']
                total_amount += item_total
                
                transaction_items.append({
                    'sku': sku,
                    'name': result[0],
                    'price': result[1],
                    'qty': item['qty'],
                    'subtotal': item_total
                })
            
            # 2. Update stok
            for item in items:
                sku = str(item['sku'])
                sql = "UPDATE produk_biasa SET stok = stok - %s WHERE no_SKU = %s"
                cursor.execute(sql, (item['qty'], sku))
            
            # 3. Simpan ke history
            transaction_id = self.generate_transaction_id()
            transaction_data = {
                'transaction_id': transaction_id,
                'user_id': user_id,
                'username': username,
                'total_amount': total_amount,
                'transaction_type': 'biasa',
                'payment_method': 'cash',
                'items_count': len(items),
                'details': json.dumps(transaction_items, ensure_ascii=False)
            }
            
            if not self.history.save_transaction(transaction_data):
                print("Warning: Gagal menyimpan transaksi ke history")
            
            self.db.commit()
            return True, f"Transaksi {transaction_id} berhasil! Total: Rp{total_amount:,}"
            
        except Error as e:
            self.db.rollback()
            return False, f"Gagal: {str(e)}"
        finally:
            cursor.close()
    
    def checkout_lelang(self, items, user_id, username):
        """Checkout transaksi lelang dengan menyimpan history"""
        if not self.db: return False, "Database tidak terhubung"
        
        cursor = self.db.cursor()
        try:
            total_amount = 0
            transaction_items = []
            
            # 1. Validasi dan hitung total
            for item in items:
                cursor.execute("SELECT Name_product, Price FROM produk_lelang WHERE no_SKU = %s", (item['sku'],))
                result = cursor.fetchone()
                
                if not result:
                    return False, f"Produk lelang {item['sku']} tidak ditemukan"
                
                item_total = result[1] * item['qty']
                total_amount += item_total
                
                transaction_items.append({
                    'sku': item['sku'],
                    'name': result[0],
                    'price': result[1],
                    'qty': item['qty'],
                    'subtotal': item_total
                })
            
            # 2. Simpan ke history
            transaction_id = self.generate_transaction_id()
            transaction_data = {
                'transaction_id': transaction_id,
                'user_id': user_id,
                'username': username,
                'total_amount': total_amount,
                'transaction_type': 'lelang',
                'payment_method': 'cash',
                'items_count': len(items),
                'details': json.dumps(transaction_items, ensure_ascii=False)
            }
            
            if not self.history.save_transaction(transaction_data):
                print("Warning: Gagal menyimpan transaksi lelang ke history")
            
            # 3. Hapus dari produk lelang
            for item in items:
                cursor.execute("DELETE FROM produk_lelang WHERE no_SKU = %s", (item['sku'],))
            
            self.db.commit()
            return True, f"Transaksi lelang {transaction_id} berhasil! Total: Rp{total_amount:,}"
            
        except Error as e:
            self.db.rollback()
            return False, f"Gagal: {str(e)}"
        finally:
            cursor.close()

class CashierSystem:
    def __init__(self):
        self.db = Database.get_conn()
        self.inventory = Inventory(self.db)
        self.transaction = Transaction(self.db)
    
    @staticmethod
    def hash_password(password):
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt)
    
    @staticmethod
    def check_password(hashed_password, password):
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password)

    def login_user(self, email_or_username, password):
        """Login dengan email ATAU username"""
        if not self.db: return None
        cursor = self.db.cursor(dictionary=True)
        try:
            # Cari user dengan email ATAU username
            sql = """
            SELECT id, username, email, password_hash, role, profile_pic
            FROM users 
            WHERE email = %s OR username = %s
            """
            cursor.execute(sql, (email_or_username, email_or_username))
            user = cursor.fetchone()
        
            if user and self.check_password(user['password_hash'], password):
                return {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'role': user['role'],
                'profile_pic': user['profile_pic'] or '/static/img/default-avatar.png'
                }
            return None
        except Error as e:
            print(f"Error login: {e}")
            return None
        finally:
            cursor.close()
    def register_user(self, username, email, whatsapp, password, role='kasir'):
        if not self.db: return False
        cursor = self.db.cursor()
        try:
            hashed_password = self.hash_password(password)
            
            sql = """
            INSERT INTO users (username, email, whatsapp, password_hash, role) 
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (username, email, whatsapp, hashed_password, role))
            self.db.commit()
            return True
        except Error as e:
            print(f"Error register: {e}")
            self.db.rollback()
            return False
        finally:
            cursor.close()

    def close(self):
        if self.db: self.db.close()