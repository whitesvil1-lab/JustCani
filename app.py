import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, url_for, flash, redirect, request, session, jsonify, send_file
from forms import RegistrationForm, LoginForm
from logic import CashierSystem, Inventory, Database
from datetime import datetime, timedelta    
import json
import base64
from werkzeug.utils import secure_filename
from io import BytesIO
import logging
import cv2
import numpy as np
from pyzbar.pyzbar import decode
import traceback
# Di app.py, tambahkan setelah Flask app creation
from flask_cors import CORS


# Atau lebih spesifik:
# CORS(app, resources={r"/api/*": {"origins": ["https://your-vercel-app.vercel.app", "http://localhost:5000"]}})

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ============================================
# CHECK DEPENDENCIES
# ============================================

# Coba import PIL, jika tidak ada, disable fitur
try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    print("INFO: Pillow not installed. Profile picture features will be limited.")

# Cek apakah barcode library tersedia
try:
    import barcode
    from barcode.writer import ImageWriter
    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False
    print("INFO: Python-barcode not installed. Barcode generation features will be limited.")

# ============================================
# APP CONFIGURATION
# ============================================
app = Flask(__name__)
CORS(app, 
     resources={
         r"/api/*": {
             "origins": ["*"],  # Allow semua origins
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
             "supports_credentials": True
         },
         r"/*": {
             "origins": ["*"],
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"]
         }
     })
 

app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY', 
    'fallback-dev-key-hanya-untuk-local'  
)


# Debug info untuk Vercel
@app.route("/api/debug/vercel")
def debug_vercel():
    """Debug khusus Vercel"""
    return jsonify({
        "status": "online",
        "platform": "vercel" if os.environ.get('VERCEL') else "localhost",
        "database_url_set": bool(os.environ.get('DATABASE_URL')),
        "python_version": sys.version,
        "flask_cors": "enabled",
        "timestamp": datetime.now().isoformat()
    })

# Upload configuration
UPLOAD_FOLDER = 'static/uploads/profile_pics'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


#upload pics
if os.environ.get('VERCEL'):
    print("🚀 Running on Vercel")
    # Vercel menggunakan /tmp untuk writeable storage
    app.config['UPLOAD_FOLDER'] = '/tmp/uploads/profile_pics'
else:
    app.config['UPLOAD_FOLDER'] = 'static/uploads/profile_pics'
def create_upload_folder():
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        print(f"✅ Upload folder: {app.config['UPLOAD_FOLDER']}")
    except Exception as e:
        print(f"⚠️ Could not create upload folder: {e}")

# Panggil saat app start
create_upload_folder()

def process_and_save_image(file, user_id):
    if not PILLOW_AVAILABLE:
        # Fallback sederhana
        filename = f"profile_{user_id}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        return f"/{UPLOAD_FOLDER}/{filename}"
    
    try:
        img = Image.open(file)
        
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[3])
            else:
                background.paste(img, mask=img.split()[1])
            img = background
        
        width, height = img.size
        min_dim = min(width, height)
        left = (width - min_dim) / 2
        top = (height - min_dim) / 2
        right = (width + min_dim) / 2
        bottom = (height + min_dim) / 2
        img = img.crop((left, top, right, bottom))
        
        img = img.resize((400, 400), Image.Resampling.LANCZOS)
        
        filename = f"profile_{user_id}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        img.save(filepath, 'JPEG', quality=85)
        
        return f"/{UPLOAD_FOLDER}/{filename}"
        
    except Exception as e:
        print(f"Error processing image: {e}")
        return None

#=============================================
# UTILITY FUNCTIONS
# ============================================

def get_time_ago(timestamp):
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    
    now = datetime.now()
    diff = now - timestamp
    
    if diff.days > 0:
        return f"{diff.days} hari lalu"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} jam lalu"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} menit lalu"
    else:
        return "Baru saja"

def scan_barcode_with_pyzbar(image):
    """
    Scan barcode menggunakan pyzbar
    Args:
        image: numpy array image (BGR or GRAY)
    Returns:
        dict: {'success': bool, 'barcode': str, 'format': str, 'polygon': list}
    """
    try:
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Decode barcodes
        decoded_objects = decode(gray)
        
        if decoded_objects:
            barcode_obj = decoded_objects[0]
            barcode_data = barcode_obj.data.decode('utf-8')
            barcode_type = barcode_obj.type
            
            # Format mapping untuk konsistensi
            format_map = {
                'CODE128': 'code_128',
                'EAN13': 'ean_13',
                'EAN8': 'ean_8',
                'UPC-A': 'upc_a',
                'UPC-E': 'upc_e',
                'CODE39': 'code_39'
            }
            
            return {
                'success': True,
                'codeResult': {
                    'code': barcode_data,
                    'format': format_map.get(barcode_type, barcode_type.lower()),
                    'decoded': barcode_data
                },
                'bounds': {
                    'x': barcode_obj.rect.left,
                    'y': barcode_obj.rect.top,
                    'width': barcode_obj.rect.width,
                    'height': barcode_obj.rect.height
                },
                'cornerPoints': [
                    {'x': point.x, 'y': point.y} 
                    for point in barcode_obj.polygon
                ]
            }
        else:
            return {
                'success': False,
                'codeResult': None,
                'message': 'No barcode detected'
            }
            
    except Exception as e:
        print(f"Error in barcode scanning: {e}")
        return {
            'success': False,
            'codeResult': None,
            'message': f'Scanning error: {str(e)}'
        }

# ============================================
# ROUTES - AUTHENTICATION & PROFILE
# ============================================

@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html', title='Home')

@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        sys = CashierSystem()
        berhasil = sys.register_user(
            form.username.data, 
            form.email.data, 
            form.whatsapp.data, 
            form.password.data
        )
        if berhasil:
            flash('Akun berhasil dibuat! Silakan login.', 'success')
            return redirect(url_for('login'))
        flash('Gagal daftar. Email/Username mungkin sudah ada.', 'danger')
    return render_template('register.html', title='Daftar', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        sys = CashierSystem()
        user = sys.login_user(form.email.data, form.password.data)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            session['role'] = user['role']
            session['profile_pic'] = user.get('profile_pic', '/static/img/default-avatar.png')
            
            flash(f'Selamat datang, {user["username"]}!', 'success')
            
            if user['role'] == 'admin':
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('kasir'))
        flash('Login gagal. Cek email/username dan password.', 'danger')
    return render_template('login.html', title='Masuk', form=form)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route("/api/upload_profile_pic", methods=['POST'])
def upload_profile_pic():
    if not session.get('user_id'):
        return jsonify({"success": False, "message": "Silakan login"})
    
    if 'photo' not in request.files:
        return jsonify({"success": False, "message": "Tidak ada file"})
    
    file = request.files['photo']
    
    if file.filename == '':
        return jsonify({"success": False, "message": "Nama file kosong"})
    
    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "Format tidak didukung"})
    
    create_upload_folder()
    
    try:
        profile_pic_url = process_and_save_image(file, session['user_id'])
        
        if not profile_pic_url:
            return jsonify({"success": False, "message": "Gagal memproses"})
        
        # Update database
        sys = CashierSystem()
        cursor = sys.db.cursor()
        sql = "UPDATE users SET profile_pic = %s WHERE id = %s"
        cursor.execute(sql, (profile_pic_url, session['user_id']))
        sys.db.commit()
        
        session['profile_pic'] = profile_pic_url
        
        return jsonify({
            "success": True, 
            "message": "Foto berhasil diupdate",
            "profile_pic": profile_pic_url
        })
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

# ============================================
# ROUTES - MAIN PAGES
# ============================================

@app.route("/kasir")
def kasir():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return render_template('kasir.html', title='Menu Kasir')

@app.route("/admin")
def admin():
    if session.get('role') != 'admin':
        flash('Akses ditolak! Anda bukan admin.', 'danger')
        return redirect(url_for('home'))
    return render_template('admin.html', title='Admin Dashboard')

@app.route("/products")
def products():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return render_template('products.html', title='Daftar Produk')

@app.route("/scanner")
def scanner_page():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return render_template('scanner.html', title='Barcode Scanner')

# ============================================
# DEBUG DB
# ============================================

@app.route("/api/debug_db")
def debug_db():
    """Simple debug endpoint - FIXED for PostgreSQL"""
    try:
        connection = Database.get_conn()
        if not connection:
            return "<h3>❌ ERROR</h3><p>Gagal koneksi ke PostgreSQL</p>"
            
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT COUNT(*) as count FROM produk_biasa")
        biasa_count = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) as count FROM produk_lelang")
        lelang_count = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) as count FROM users")
        user_count = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        return f"""
        <div style="font-family: sans-serif; padding: 20px;">
            <h3>📊 Database Cloud Status (Neon/Postgres)</h3>
            <hr>
            <p>✅ <b>Koneksi:</b> Berhasil</p>
            <p>📦 <b>Produk Biasa:</b> {biasa_count['count']} item</p>
            <p>🔨 <b>Produk Lelang:</b> {lelang_count['count']} item</p>
            <p>👤 <b>Total User:</b> {user_count['count']} user</p>
            <br>
            <a href="/">Kembali ke Dashboard</a>
        </div>
        """
    except Exception as e:
        return f"<div style='color:red;'><h3>❌ ERROR</h3><p>{str(e)}</p></div>"
    
@app.route("/api/debug/test_db")
def debug_test_db():
    """Test koneksi database dan cek tabel"""
    try:
        from logic import Database
        conn = Database.get_conn()
        
        if not conn:
            return jsonify({"success": False, "error": "No database connection"})
        
        cursor = conn.cursor()
        
        # Cek tabel transaction_history
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'transaction_history'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        # Cek data produk
        cursor.execute("SELECT no_sku, name_product, price, stok FROM produk_biasa LIMIT 5")
        products = cursor.fetchall()
        
        # Cek data transaksi
        cursor.execute("SELECT COUNT(*) as count FROM transaction_history")
        transaction_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "transaction_table_exists": table_exists,
            "transaction_count": transaction_count,
            "sample_products": [
                {
                    "sku": p[0],
                    "name": p[1],
                    "price": float(p[2]) if p[2] else 0,
                    "stock": p[3]
                }
                for p in products
            ]
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    
@app.route("/api/debug/search")
def debug_search():
    """Debug endpoint untuk test search"""
    try:
        connection = Database.get_conn()
        if not connection:
            return jsonify({"error": "No database connection"}), 500
        
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        # Test query sederhana
        cursor.execute("SELECT COUNT(*) as count FROM produk_biasa")
        biasa_count = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) as count FROM produk_lelang")
        lelang_count = cursor.fetchone()
        
        cursor.execute("SELECT no_sku, name_product, price FROM produk_biasa LIMIT 5")
        sample_products = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            "status": "ok",
            "counts": {
                "produk_biasa": biasa_count['count'],
                "produk_lelang": lelang_count['count']
            },
            "sample_products": sample_products
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

@app.route("/api/create_transaction_table", methods=['GET', 'POST'])
def create_transaction_table():
    """Buat tabel transaction_history jika belum ada"""
    try:
        from logic import Database
        import psycopg2
        
        conn = Database.get_conn()
        if not conn:
            return jsonify({"success": False, "error": "No database connection"})
        
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'transaction_history'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            cursor.close()
            conn.close()
            return jsonify({
                "success": True,
                "message": "Tabel transaction_history sudah ada",
                "table_exists": True
            })
        
        # Create table
        print("🔄 Creating transaction_history table...")
        
        cursor.execute("""
            CREATE TABLE transaction_history (
                id SERIAL PRIMARY KEY,
                transaction_id VARCHAR(50) UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                username VARCHAR(100) NOT NULL,
                total_amount DECIMAL(10,2) NOT NULL,
                transaction_type VARCHAR(20) NOT NULL DEFAULT 'biasa',
                payment_method VARCHAR(20) DEFAULT 'cash',
                items_count INTEGER NOT NULL,
                details TEXT NOT NULL,
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX idx_transaction_date 
            ON transaction_history(transaction_date DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX idx_transaction_user 
            ON transaction_history(user_id)
        """)
        
        conn.commit()
        
        # Verify
        cursor.execute("SELECT COUNT(*) FROM transaction_history")
        count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Tabel transaction_history berhasil dibuat!",
            "table_created": True,
            "initial_count": count
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })


@app.route("/api/debug/tables")
def debug_tables():
    """Cek struktur tabel"""
    try:
        connection = Database.get_conn()
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name IN ('produk_biasa', 'produk_lelang')
            ORDER BY table_name, ordinal_position
        """)
        
        columns = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        html = "<h3>Table Structure</h3><table border='1'><tr><th>Table</th><th>Column</th><th>Type</th></tr>"
        for col in columns:
            html += f"<tr><td>{col[0]}</td><td>{col[1]}</td><td>{col[2]}</td></tr>"
        html += "</table>"
        
        return html
        
    except Exception as e:
        return f"<pre>Error: {str(e)}</pre>"

# ============================================
# ROUTES - ADMIN FEATURES
# ============================================

@app.route("/admin/dashboard")
def admin_dashboard():
    if session.get('role') != 'admin':
        flash('Akses ditolak! Hanya admin.', 'danger')
        return redirect(url_for('home'))
    return render_template('admin_dashboard.html', title='Dashboard Statistik')

@app.route("/admin/history")
def admin_history():
    if session.get('role') != 'admin':
        flash('Akses ditolak! Hanya admin.', 'danger')
        return redirect(url_for('home'))
    
    date_filter = request.args.get('date', '')
    
    sys = CashierSystem()
    
    if date_filter:
        transactions = sys.transaction.history.get_transactions_by_date(date_filter, date_filter)
    else:
        transactions = sys.transaction.history.get_all_transactions(limit=100)
    
    today = datetime.now().strftime("%Y-%m-%d")
    daily_summary = sys.transaction.history.get_daily_summary(today)
    
    return render_template('admin_history.html', 
                         title='History Transaksi',
                         transactions=transactions,
                         daily_summary=daily_summary,
                         date_filter=date_filter)

@app.route("/admin/add", methods=['POST'])
def admin_add():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    sys = CashierSystem()
    sku = request.form.get('sku')
    name = request.form.get('name')
    harga = request.form.get('harga')
    expired_date = request.form.get('expired_date')
    
    if BARCODE_AVAILABLE and sku:
        try:
            code128 = barcode.get_barcode_class('code128')
            barcode_instance = code128(str(sku), writer=ImageWriter())
            
            buffer = BytesIO()
            barcode_instance.write(buffer)
            buffer.seek(0)
            
            barcode_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            barcode_data = f"data:image/png;base64,{barcode_base64}"
            
            sys.inventory.save_barcode_to_db(sku, barcode_data)
            print(f"✅ Barcode auto-generated for SKU: {sku}")
            
        except Exception as e:
            print(f"⚠️ Barcode generation failed: {e}")
    
    sys.inventory.add_produk_baru(sku, name, harga, expired_date)
    
    flash('Produk berhasil ditambahkan!', 'success')
    return redirect(url_for('admin'))

@app.route("/admin/restock", methods=['POST'])
def admin_restock():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    sys = CashierSystem()
    cursor = sys.db.cursor()
    sql = "UPDATE produk_biasa SET stok = stok + %s WHERE no_SKU = %s"
    cursor.execute(sql, (request.form.get('qty'), request.form.get('sku')))
    sys.db.commit()
    flash('Stok berhasil diperbarui!', 'success')
    return redirect(url_for('admin'))

@app.route("/admin/move_lelang", methods=['POST'])
def admin_move_lelang():
    if session.get('role') != 'admin':
        flash('Akses ditolak! Hanya admin yang bisa pindah ke lelang.', 'danger')
        return redirect(url_for('admin'))
    
    sku = request.form.get('sku')
    reason = request.form.get('reason')
    
    if not sku or not reason:
        flash('SKU dan alasan harus diisi!', 'danger')
        return redirect(url_for('admin'))
    
    sys = CashierSystem()
    success, message = sys.inventory.move_to_lelang(sku, reason)
    
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('admin'))

# ============================================
# API ENDPOINTS - PRODUCTS & TRANSACTIONS
# ============================================

@app.route("/api/search")
def api_search():
    """API untuk search produk biasa - DIRECT QUERY VERSION"""
    try:
        query = request.args.get('q', '')
        print(f"[DEBUG] Direct search produk biasa: '{query}'")
        
        connection = Database.get_conn()
        if not connection:
            return jsonify({"results": []}), 200
        
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        # Direct query tanpa Inventory class
        sql = """
        SELECT 
            no_sku as "no_SKU",
            name_product as "Name_product",
            price as "Price",
            expired_date,
            COALESCE(stok, 0) as stok
        FROM produk_biasa 
        WHERE name_product ILIKE %s OR CAST(no_sku AS VARCHAR) ILIKE %s
        ORDER BY name_product
        LIMIT 50
        """
        
        search_pattern = f"%{query}%" if query else "%"
        cursor.execute(sql, (search_pattern, search_pattern))
        results = cursor.fetchall()
        
        print(f"[DEBUG] Direct search found {len(results)} results")
        
        # Format results
        formatted = []
        for r in results:
            item = {
                'no_SKU': r['no_SKU'],
                'Name_product': r['Name_product'],
                'Price': float(r['Price']) if r['Price'] else 0,
                'stok': int(r['stok']) if r['stok'] else 0
            }
            
            if r['expired_date']:
                if isinstance(r['expired_date'], datetime):
                    item['expired_date'] = r['expired_date'].isoformat()
                else:
                    item['expired_date'] = str(r['expired_date'])
            
            formatted.append(item)
        
        cursor.close()
        connection.close()
        
        return jsonify(formatted)
        
    except Exception as e:
        print(f"[ERROR] Direct api_search failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "results": []}), 500

#debug lelang
@app.route("/api/debug/lelang_products")
def debug_lelang_products():
    """Debug endpoint untuk produk lelang"""
    try:
        from logic import Database
        
        conn = Database.get_conn()
        if not conn:
            return jsonify({"error": "No database connection"}), 500
        
        cursor = conn.cursor()
        
        print("🔍 Debugging produk lelang...")
        
        # 1. Cek tabel exist
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'produk_lelang'
            )
        """)
        table_exists = cursor.fetchone()[0]
        print(f"Table exists: {table_exists}")
        
        # 2. Cek struktur
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'produk_lelang'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        print(f"Columns: {columns}")
        
        # 3. Cek data
        cursor.execute("SELECT COUNT(*) FROM produk_lelang")
        count = cursor.fetchone()[0]
        print(f"Total records: {count}")
        
        # 4. Get sample data
        cursor.execute("SELECT * FROM produk_lelang LIMIT 5")
        sample_data = cursor.fetchall()
        print(f"Sample data: {sample_data}")
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "table_exists": table_exists,
            "columns": columns,
            "total_records": count,
            "sample_data": sample_data
        })
        
    except Exception as e:
        import traceback
        print(f"❌ Debug error: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500



# api lelang

@app.route("/api/search_lelang")
def api_search_lelang():
    """API untuk search produk lelang - FIXED VERSION"""
    print(f"[API] Search lelang called: q={request.args.get('q', '')}")
    
    try:
        # Direct query tanpa melalui Inventory class
        from logic import Database
        from datetime import datetime
        
        conn = Database.get_conn()
        if not conn:
            print("[API] No database connection")
            return jsonify([]), 200
        
        cursor = conn.cursor()
        
        query = request.args.get('q', '')
        search_pattern = f"%{query}%" if query else "%"
        
        print(f"[API] Searching with pattern: {search_pattern}")
        
        # ✅ SIMPLE QUERY dengan semua kolom
        sql = """
        SELECT 
            no_sku,
            name_product,
            price,
            expired_date,
            barcode_image
        FROM produk_lelang 
        WHERE name_product ILIKE %s OR CAST(no_sku AS VARCHAR) ILIKE %s
        ORDER BY name_product
        LIMIT 50
        """
        
        cursor.execute(sql, (search_pattern, search_pattern))
        results = cursor.fetchall()
        
        print(f"[API] Found {len(results)} lelang products")
        
        # Format untuk frontend
        formatted = []
        for row in results:
            # Debug setiap row
            print(f"[API] Row data: {row}")
            
            # Convert row tuple to dictionary
            item = {
                'no_SKU': row[0],          # no_sku
                'Name_product': row[1],     # name_product
                'Price': row[2],            # price
                'type': 'lelang'
            }
            
            # Format expired_date jika ada
            if row[3]:
                try:
                    if isinstance(row[3], datetime):
                        item['expired_date'] = row[3].isoformat()
                    else:
                        # Jika string, parse dulu
                        item['expired_date'] = str(row[3])
                except Exception as e:
                    print(f"[API] Date format error: {e}")
                    item['expired_date'] = str(row[3])
            
            # Tambah barcode jika ada
            if row[4]:
                item['barcode_image'] = row[4]
            
            formatted.append(item)
            print(f"[API] Formatted item: {item}")
        
        cursor.close()
        conn.close()
        
        print(f"[API] Returning {len(formatted)} items")
        return jsonify(formatted)
        
    except Exception as e:
        print(f"[ERROR] api_search_lelang: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "results": []}), 500
    

@app.route("/api/checkout", methods=['POST'])
def api_checkout():
    """API untuk checkout - FIXED VERSION"""
    print("=" * 50)
    print("🛒 [API CHECKOUT] DIPANGGIL")
    print("=" * 50)
    
    # 1. Cek session user
    if not session.get('user_id'):
        print("❌ User belum login")
        return jsonify({
            "success": False, 
            "message": "Silakan login terlebih dahulu"
        })
    
    print(f"👤 User: {session.get('username')} (ID: {session.get('user_id')})")
    
    try:
        # 2. Ambil data dari request
        data = request.get_json()
        print(f"📦 Data diterima: {data}")
        
        if not data:
            print("❌ Tidak ada data JSON")
            return jsonify({
                "success": False, 
                "message": "Data tidak valid"
            })
        
        if 'items' not in data:
            print("❌ Key 'items' tidak ditemukan")
            return jsonify({
                "success": False, 
                "message": "Data items tidak ditemukan"
            })
        
        items = data['items']
        print(f"📊 Jumlah item: {len(items)}")
        
        if len(items) == 0:
            print("❌ Keranjang kosong")
            return jsonify({
                "success": False, 
                "message": "Keranjang kosong"
            })
        
        # 3. Tampilkan detail item
        for i, item in enumerate(items):
            print(f"   Item {i+1}: SKU={item.get('sku')}, Qty={item.get('qty')}")
        
        # 4. Proses checkout
        sys = CashierSystem()
        
        if not sys.db:
            print("❌ Koneksi database gagal")
            return jsonify({
                "success": False, 
                "message": "Database tidak terhubung"
            })
        
        print("🔄 Memproses checkout...")
        success, message = sys.transaction.checkout(
            items,
            session['user_id'],
            session['username']
        )
        
        print(f"📝 Hasil checkout: {'✅ BERHASIL' if success else '❌ GAGAL'}")
        print(f"📝 Pesan: {message}")
        print("=" * 50)
        
        return jsonify({
            "success": success,
            "message": message
        })
        
    except Exception as e:
        print(f"🔥 ERROR dalam API: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "success": False,
            "message": f"Server error: {str(e)}"
        })
    


@app.route("/api/checkout_lelang", methods=['POST'])
def api_checkout_lelang():
    if not session.get('user_id'):
        return jsonify({"success": False, "message": "Silakan login terlebih dahulu"})
    
    data = request.json
    sys = CashierSystem()
    success, msg = sys.transaction.checkout_lelang(
        data['items'],
        session['user_id'],
        session['username']
    )
    return jsonify({"success": success, "message": msg})

@app.route("/api/transaction/<int:transaction_id>")
def api_transaction_detail(transaction_id):
    if session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    
    sys = CashierSystem()
    cursor = sys.db.cursor(cursor_factory=RealDictCursor)
    try:
        sql = "SELECT * FROM transaction_history WHERE id = %s"
        cursor.execute(sql, (transaction_id,))
        transaction = cursor.fetchone()
        
        if not transaction:
            return jsonify({"error": "Transaction not found"}), 404
        
        return jsonify(transaction)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

@app.route("/api/debug/checkout_test", methods=['POST'])
def debug_checkout_test():
    """Test endpoint untuk checkout"""
    try:
        data = request.json
        print(f"[DEBUG TEST] Test data: {data}")
        
        # Test database connection
        sys = CashierSystem()
        if not sys.db:
            return jsonify({"success": False, "error": "No database connection"})
        
        # Test query produk
        cursor = sys.db.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT no_sku, name_product, price, stok FROM produk_biasa LIMIT 5")
        products = cursor.fetchall()
        
        # Test insert ke transaction_history
        test_data = {
            'transaction_id': f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'user_id': 1,
            'username': 'test_user',
            'total_amount': 10000,
            'transaction_type': 'biasa',
            'payment_method': 'cash',
            'items_count': 1,
            'details': json.dumps([{"sku": "12345", "name": "Test Product", "qty": 1, "price": 10000}])
        }
        
        # Cek struktur tabel
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'transaction_history'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        
        cursor.close()
        
        return jsonify({
            "success": True,
            "database": "connected",
            "products_sample": products,
            "table_columns": columns,
            "test_data": test_data,
            "message": "Debug test successful"
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })

@app.route("/api/debug_cart", methods=['POST'])
def debug_cart():
    """Debug endpoint untuk test cart"""
    try:
        data = request.json
        print(f"[DEBUG CART] Received data: {data}")
        
        # Simulate successful checkout
        return jsonify({
            "success": True,
            "message": "Transaksi test berhasil!",
            "transaction_id": f"TRX-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "total_items": len(data.get('items', [])),
            "data_received": data
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/test_db")
def test_db():
    """Test database connection"""
    try:
        conn = Database.get_conn()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return jsonify({"success": True, "message": "Database OK"})
        else:
            return jsonify({"success": False, "message": "Database connection failed"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ============================================
# API ENDPOINTS - STATISTICS & REPORTS
# ============================================

@app.route("/api/stats")
def api_stats():
    if session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        from logic import Database
        from datetime import datetime, timedelta
        
        conn = Database.get_conn()
        cursor = conn.cursor()
        
        # Today's stats
        today = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_transactions,
                COALESCE(SUM(total_amount), 0) as total_revenue,
                COALESCE(SUM(items_count), 0) as total_items
            FROM transaction_history 
            WHERE DATE(transaction_date) = %s
        """, (today,))
        
        today_stats = cursor.fetchone()
        
        # Weekly stats
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT 
                DATE(transaction_date) as date,
                COUNT(*) as daily_transactions,
                COALESCE(SUM(total_amount), 0) as daily_revenue
            FROM transaction_history 
            WHERE transaction_date >= %s
            GROUP BY DATE(transaction_date)
            ORDER BY date DESC
        """, (week_ago,))
        
        weekly_data = cursor.fetchall()
        
        # Top products
        cursor.execute("""
            SELECT 
                d->>'name' as product_name,
                SUM(CAST(d->>'qty' as INTEGER)) as total_sold,
                SUM(CAST(d->>'subtotal' as NUMERIC)) as total_revenue
            FROM transaction_history,
            json_array_elements(details::json) as d
            WHERE transaction_date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY d->>'name'
            ORDER BY total_sold DESC
            LIMIT 5
        """)
        
        top_products = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "today": {
                "transactions": today_stats[0],
                "revenue": float(today_stats[1]),
                "items": today_stats[2]
            },
            "weekly": [
                {
                    "date": row[0].strftime('%Y-%m-%d'),
                    "transactions": row[1],
                    "revenue": float(row[2])
                }
                for row in weekly_data
            ],
            "top_products": [
                {
                    "name": row[0],
                    "sold": row[1],
                    "revenue": float(row[2])
                }
                for row in top_products
            ]
        })
        
    except Exception as e:
        print(f"Error getting stats: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================
# API ENDPOINTS - BARCODE MANAGEMENT
# ============================================

@app.route("/api/scan_barcode", methods=['POST'])
def scan_barcode():
    """API untuk scan barcode menggunakan pyzbar"""
    if not session.get('user_id'):
        return jsonify({"success": False, "message": "Silakan login terlebih dahulu"})
    
    try:
        if 'image' not in request.files:
            data = request.json
            if not data or 'image' not in data:
                return jsonify({"success": False, "message": "Tidak ada gambar"})
            
            # Decode base64 image
            image_data = data['image'].split(',')[1] if ',' in data['image'] else data['image']
            nparr = np.frombuffer(base64.b64decode(image_data), np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Scan barcode with pyzbar
            result = scan_barcode_with_pyzbar(img)
            
            if result['success']:
                barcode_code = result['codeResult']['code']
                print(f"[DEBUG] Barcode yang discan: '{barcode_code}'")
                print(f"[DEBUG] Tipe data barcode: {type(barcode_code)}")
                
                # Cari produk di database
                sys = CashierSystem()
                cursor = sys.db.cursor(cursor_factory=RealDictCursor)
                
                # === PERUBAHAN: Coba convert ke integer ===
                try:
                    # Coba convert barcode ke integer
                    sku_int = int(barcode_code)
                    
                    # Cari di produk biasa dengan integer
                    cursor.execute("""
                        SELECT no_SKU as sku, Name_product as name, Price as price, stok, 'biasa' as type
                        FROM produk_biasa 
                        WHERE no_SKU = %s
                    """, (sku_int,))
                    product = cursor.fetchone()
                    
                    if not product:
                        # Cari di produk lelang
                        cursor.execute("""
                            SELECT no_SKU as sku, Name_product as name, Price as price, 'lelang' as type
                            FROM produk_lelang 
                            WHERE no_SKU = %s
                        """, (sku_int,))
                        product = cursor.fetchone()
                        
                except ValueError:
                    # Jika barcode bukan angka, cari sebagai string
                    cursor.execute("""
                        SELECT no_SKU as sku, Name_product as name, Price as price, stok, 'biasa' as type
                        FROM produk_biasa 
                        WHERE CAST(no_SKU AS TEXT) = %s
                    """, (barcode_code,))
                    product = cursor.fetchone()
                    
                    if not product:
                        cursor.execute("""
                            SELECT no_SKU as sku, Name_product as name, Price as price, 'lelang' as type
                            FROM produk_lelang 
                            WHERE CAST(no_SKU AS TEXT) = %s
                        """, (barcode_code,))
                        product = cursor.fetchone()
                
                cursor.close()
                
                if product:
                    return jsonify({
                        "success": True,
                        "barcode": barcode_code,
                        "barcode_format": result['codeResult']['format'],
                        "product": product,
                        "scan_result": result
                    })
                else:
                    return jsonify({
                        "success": False,
                        "message": f"Produk dengan SKU {barcode_code} tidak ditemukan",
                        "barcode": barcode_code,
                        "barcode_format": result['codeResult']['format']
                    })
            
            return jsonify({
                "success": False,
                "message": result.get('message', 'Barcode tidak terdeteksi'),
                "scan_result": result
            })
            
    except Exception as e:
        print(f"Error scanning barcode: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        })
    
    return jsonify({"success": False, "message": "Gagal memproses"})

@app.route("/api/products/for_barcode")
def api_products_for_barcode():
    """Get all products for barcode dropdown"""
    if not session.get('user_id'):
        return jsonify({"error": "Unauthorized"}), 401
    
    connection = Database.get_conn()
    if not connection:
        return jsonify({"success": False, "error": "Gagal koneksi database"}), 500
        
    try:
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        products = []
        
        cursor.execute("""
            SELECT 
                no_sku as sku, 
                name_product as name, 
                price as price,
                'biasa' as type,
                CASE 
                    WHEN barcode_image IS NOT NULL AND barcode_image != '' THEN 1
                    ELSE 0 
                END as has_barcode
            FROM produk_biasa 
            ORDER BY name_product
        """)
        regular = cursor.fetchall()
        products.extend(regular)
        
        cursor.execute("""
            SELECT 
                no_sku as sku, 
                name_product as name, 
                price as price,
                'lelang' as type,
                CASE 
                    WHEN barcode_image IS NOT NULL AND barcode_image != '' THEN 1
                    ELSE 0 
                END as has_barcode
            FROM produk_lelang 
            ORDER BY name_product
        """)
        auction = cursor.fetchall()
        products.extend(auction)
        
        print(f"[DEBUG] Found {len(products)} products for barcode dropdown")
        
        return jsonify({
            "success": True,
            "products": products,
            "count": len(products)
        })
        
    except Exception as e:
        print(f"[ERROR] api_products_for_barcode: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if connection: connection.close()

@app.route("/api/barcode/<sku>/image")
def get_barcode_image(sku):
    """Get existing barcode image"""
    sys = CashierSystem()
    cursor = sys.db.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT barcode_image 
            FROM produk_biasa 
            WHERE no_SKU = %s AND barcode_image IS NOT NULL
        """, (sku,))
        result = cursor.fetchone()
        
        if not result:
            cursor.execute("""
                SELECT barcode_image 
                FROM produk_lelang 
                WHERE no_SKU = %s AND barcode_image IS NOT NULL
            """, (sku,))
            result = cursor.fetchone()
        
        if result and result['barcode_image']:
            return jsonify({
                "success": True,
                "barcode": result['barcode_image']
            })
        
        return jsonify({"success": False, "message": "Barcode tidak ditemukan"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()

@app.route("/api/barcode/generate_all", methods=['POST'])
def generate_all_barcodes():
    """Generate barcode untuk semua produk yang belum punya"""
    if session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    
    connection = Database.get_conn()
    if not connection:
        return jsonify({"success": False, "error": "Database connection failed"}), 500
        
    try:
        inventory = Inventory(connection)
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT no_sku, name_product, price 
            FROM produk_biasa 
            WHERE barcode_image IS NULL OR barcode_image = ''
        """)
        biasa = cursor.fetchall()
        
        cursor.execute("""
            SELECT no_sku, name_product, price 
            FROM produk_lelang 
            WHERE barcode_image IS NULL OR barcode_image = ''
        """)
        lelang = cursor.fetchall()
        
        all_products = biasa + lelang
        generated = 0
        
        for product in all_products:
            try:
                barcode_data = inventory.generate_product_barcode(
                    product['no_sku'], 
                    product['name_product'], 
                    product['price']
                )
                
                if barcode_data:
                    table = "produk_biasa" if any(p['no_sku'] == product['no_sku'] for p in biasa) else "produk_lelang"
                    
                    cursor.execute(f"""
                        UPDATE {table} 
                        SET barcode_image = %s 
                        WHERE no_sku = %s
                    """, (barcode_data, product['no_sku']))
                    
                    generated += 1
            except Exception as e:
                print(f"Gagal generate SKU {product['no_sku']}: {e}")
                continue
        
        connection.commit()
        
        return jsonify({
            "success": True,
            "message": f"Berhasil membuat {generated} barcode dari {len(all_products)} produk",
            "total": len(all_products),
            "generated": generated
        })
        
    except Exception as e:
        if connection: connection.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if connection: connection.close()

@app.route("/api/barcode/status")
def api_barcode_status():
    """Get barcode generation status"""
    if not session.get('user_id'):
        return jsonify({"error": "Unauthorized"}), 401
    
    sys = CashierSystem()
    cursor = sys.db.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("SELECT COUNT(*) as total FROM produk_biasa")
        regular_total = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM produk_lelang")
        auction_total = cursor.fetchone()['total']
        total_products = regular_total + auction_total
        
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM produk_biasa 
            WHERE barcode_image IS NOT NULL AND barcode_image != ''
        """)
        regular_with = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM produk_lelang 
            WHERE barcode_image IS NOT NULL AND barcode_image != ''
        """)
        auction_with = cursor.fetchone()['count']
        total_with = regular_with + auction_with
        
        progress = round((total_with / total_products * 100), 2) if total_products > 0 else 0
        
        return jsonify({
            "success": True,
            "status": {
                "total_products": total_products,
                "with_barcode": total_with,
                "without_barcode": total_products - total_with,
                "progress_percentage": progress
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()

@app.route("/admin/history/monthly")
def admin_monthly_report():
    if session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    
    year = request.args.get('year', datetime.now().year)
    month = request.args.get('month', datetime.now().month)
    
    sys = CashierSystem()
    report = sys.transaction.history.get_monthly_report(year, month)
    return jsonify(report)

# ============================================
# API ENDPOINTS - BARCODE FEATURES
# ============================================

@app.route("/api/barcode/<sku>")
def generate_barcode(sku):
    """Generate barcode image untuk produk"""
    try:
        sys = CashierSystem()
        cursor = sys.db.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT no_SKU, Name_product, Price FROM produk_biasa WHERE no_SKU = %s", (sku,))
        product = cursor.fetchone()
        
        if not product:
            cursor.execute("SELECT no_SKU, Name_product, Price FROM produk_lelang WHERE no_SKU = %s", (sku,))
            product = cursor.fetchone()
        
        if not product:
            cursor.close()
            return jsonify({
                "success": False,
                "message": f"Produk dengan SKU {sku} tidak ditemukan"
            }), 404
        
        try:
            cursor.execute("SELECT barcode_image FROM produk_biasa WHERE no_SKU = %s AND barcode_image IS NOT NULL", (sku,))
            result = cursor.fetchone()
            
            if result and result['barcode_image']:
                cursor.close()
                return jsonify({
                    "success": True,
                    "sku": sku,
                    "barcode": result['barcode_image'],
                    "cached": True,
                    "product": product
                })
        except:
            pass
        
        if not BARCODE_AVAILABLE:
            cursor.close()
            return jsonify({
                "success": False,
                "message": "Library barcode tidak terinstall. Install: pip install python-barcode"
            }), 500
        
        code128 = barcode.get_barcode_class('code128')
        barcode_instance = code128(str(sku), writer=ImageWriter())
        
        buffer = BytesIO()
        barcode_instance.write(buffer)
        buffer.seek(0)
        
        barcode_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        barcode_data = f"data:image/png;base64,{barcode_base64}"
        
        try:
            cursor.execute("""
                UPDATE produk_biasa 
                SET barcode_image = %s 
                WHERE no_SKU = %s
            """, (barcode_data, sku))
            
            cursor.execute("""
                UPDATE produk_lelang 
                SET barcode_image = %s 
                WHERE no_SKU = %s
            """, (barcode_data, sku))
            
            sys.db.commit()
        except Exception as e:
            print(f"Warning: Could not save barcode to database: {e}")
        
        cursor.close()
        
        return jsonify({
            "success": True,
            "sku": sku,
            "barcode": barcode_data,
            "cached": False,
            "product": product
        })
        
    except Exception as e:
        print(f"Error generating barcode: {e}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

@app.route("/api/barcode/<sku>/download")
def download_barcode(sku):
    """Download barcode as PNG file"""
    try:
        if not BARCODE_AVAILABLE:
            return jsonify({
                "success": False,
                "message": "Library barcode tidak terinstall"
            }), 500
        
        code128 = barcode.get_barcode_class('code128')
        barcode_instance = code128(str(sku), writer=ImageWriter())
        
        buffer = BytesIO()
        barcode_instance.write(buffer)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='image/png',
            as_attachment=True,
            download_name=f'barcode_{sku}.png'
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/barcode/status/<sku>")
def check_barcode_status(sku):
    """Cek status barcode produk"""
    if not session.get('user_id'):
        return jsonify({"error": "Unauthorized"}), 401
    
    sys = CashierSystem()
    cursor = sys.db.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT no_SKU, Name_product, barcode_image 
            FROM produk_biasa 
            WHERE no_SKU = %s
        """, (sku,))
        
        result = cursor.fetchone()
        
        if not result:
            cursor.execute("""
                SELECT no_SKU, Name_product, barcode_image 
                FROM produk_lelang 
                WHERE no_SKU = %s
            """, (sku,))
            result = cursor.fetchone()
        
        if not result:
            return jsonify({
                "success": False,
                "message": "Produk tidak ditemukan"
            }), 404
        
        has_barcode = result['barcode_image'] is not None and result['barcode_image'] != ''
        
        return jsonify({
            "success": True,
            "sku": sku,
            "product_name": result['Name_product'],
            "has_barcode": has_barcode,
            "message": "Produk sudah memiliki barcode" if has_barcode else "Produk belum memiliki barcode"
        })
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cursor.close()

@app.route("/api/products/without_barcode")
def api_products_without_barcode():
    """Get all products without barcode"""
    if session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    
    sys = CashierSystem()
    cursor = sys.db.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT no_SKU, Name_product, Price, stok 
            FROM produk_biasa 
            WHERE barcode_image IS NULL OR barcode_image = ''
        """)
        regular = cursor.fetchall()
        
        cursor.execute("""
            SELECT no_SKU, Name_product, Price 
            FROM produk_lelang 
            WHERE barcode_image IS NULL OR barcode_image = ''
        """)
        auction = cursor.fetchall()
        
        products = []
        for p in regular:
            products.append({
                'no_SKU': p['no_SKU'],
                'Name_product': p['Name_product'],
                'Price': p['Price'],
                'type': 'biasa',
                'stok': p['stok']
            })
        
        for p in auction:
            products.append({
                'no_SKU': p['no_SKU'],
                'Name_product': p['Name_product'],
                'Price': p['Price'],
                'type': 'lelang',
                'stok': None
            })
        
        return jsonify(products)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

@app.route("/api/print_barcode/<sku>")
def print_barcode_label(sku):
    """Generate printable barcode label"""
    if session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    
    sys = CashierSystem()
    cursor = sys.db.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("SELECT Name_product, Price FROM produk_biasa WHERE no_SKU = %s", (sku,))
        product = cursor.fetchone()
        
        if not product:
            cursor.execute("SELECT Name_product, Price FROM produk_lelang WHERE no_SKU = %s", (sku,))
            product = cursor.fetchone()
        
        if not product:
            return jsonify({"error": "Produk tidak ditemukan"}), 404
        
        barcode_url = f"https://barcode.tec-it.com/barcode.ashx?data={sku}&code=Code128&dpi=96"
        
        html_label = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Barcode Label - {sku}</title>
            <style>
                @media print {{
                    body {{ margin: 0; padding: 0; }}
                    .label {{ page-break-inside: avoid; }}
                }}
                body {{ font-family: Arial, sans-serif; padding: 10px; }}
                .label {{ 
                    width: 3in; 
                    height: 1.5in; 
                    border: 1px solid #000; 
                    padding: 8px;
                    margin: 5px;
                    display: inline-block;
                    vertical-align: top;
                    box-sizing: border-box;
                }}
                .product-name {{ 
                    font-size: 12px; 
                    font-weight: bold; 
                    margin-bottom: 3px;
                    height: 30px;
                    overflow: hidden;
                }}
                .sku {{ 
                    font-size: 10px; 
                    color: #666;
                    margin-bottom: 3px;
                }}
                .price {{ 
                    font-size: 14px; 
                    font-weight: bold; 
                    color: #d00;
                    margin-bottom: 5px;
                }}
                .barcode {{ 
                    margin: 3px 0;
                    text-align: center;
                }}
                .print-info {{
                    font-size: 8px; 
                    text-align: center;
                    color: #666;
                    margin-top: 3px;
                }}
            </style>
        </head>
        <body>
            <div class="label">
                <div class="product-name">{product['Name_product'][:25]}</div>
                <div class="sku">SKU: {sku}</div>
                <div class="price">Rp{int(product['Price']):,}</div>
                <div class="barcode">
                    <img src="{barcode_url}" 
                         alt="Barcode {sku}" 
                         width="180" 
                         height="40">
                </div>
                <div class="print-info">JustCani POS System</div>
            </div>
        </body>
        </html>
        """
        
        return html_label
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()

# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == '__main__':
    create_upload_folder()
    
    img_dir = 'static/img'
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)
    
    print("=" * 50)
    print("🚀 JustCani POS System Starting...")
    print(f"📦 Barcode Support: {'✅ Enabled' if BARCODE_AVAILABLE else '⚠️ Not Available'}")
    print(f"📷 Barcode Scanner: ✅ Pyzbar Ready")
    print(f"🖼️  Image Support: {'✅ Enabled' if PILLOW_AVAILABLE else '⚠️ Not Available'}")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)