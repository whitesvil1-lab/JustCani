from flask import Flask, render_template, url_for, flash, redirect, request, session, jsonify
from forms import RegistrationForm, LoginForm
from logic import CashierSystem
from datetime import datetime, timedelta    
import json
import os
from werkzeug.utils import secure_filename

# Coba import PIL, jika tidak ada, disable fitur
try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    print("WARNING: Pillow not installed. Profile picture features will be limited.")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'justcani-secret-key-2025'

# ✅ KONFIGURASI UPLOAD
UPLOAD_FOLDER = 'static/uploads/profile_pics'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_upload_folder():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

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

# ✅ ROUTE UPLOAD FOTO PROFIL (HANYA SATU!)
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
        sys.close()
        
        session['profile_pic'] = profile_pic_url
        
        return jsonify({
            "success": True, 
            "message": "Foto berhasil diupdate",
            "profile_pic": profile_pic_url
        })
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

# ✅ UPDATE ROUTE LOGIN UNTUK AMBIL PROFILE_PIC
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

# ✅ SISA ROUTE YANG SUDAH ADA (jangan duplikat!)
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
        sys.close()
        if berhasil:
            flash('Akun berhasil dibuat! Silakan login.', 'success')
            return redirect(url_for('login'))
        flash('Gagal daftar. Email/Username mungkin sudah ada.', 'danger')
    return render_template('register.html', title='Daftar', form=form)

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

@app.route("/admin/dashboard")
def admin_dashboard():
    if session.get('role') != 'admin':
        flash('Akses ditolak! Hanya admin.', 'danger')
        return redirect(url_for('home'))
    return render_template('admin_dashboard.html', title='Dashboard Statistik')

@app.route("/api/stats")
def api_stats():
    if session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    
    period = request.args.get('period', 'today')
    end_date = datetime.now()
    
    if period == 'today':
        start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'week':
        start_date = end_date - timedelta(days=7)
    elif period == 'month':
        start_date = end_date - timedelta(days=30)
    else:
        start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    sys = CashierSystem()
    
    try:
        cursor = sys.db.cursor(dictionary=True)
        start_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_str = end_date.strftime('%Y-%m-%d %H:%M:%S')
        
        sql = """
        SELECT * FROM transaction_history 
        WHERE transaction_date BETWEEN %s AND %s
        ORDER BY transaction_date DESC
        """
        cursor.execute(sql, (start_str, end_str))
        transactions = cursor.fetchall()
        
        total_revenue = sum(t['total_amount'] for t in transactions)
        total_transactions = len(transactions)
        avg_transaction = total_revenue / total_transactions if total_transactions > 0 else 0
        
        total_products = 0
        for t in transactions:
            try:
                details = json.loads(t['details'])
                total_products += sum(item.get('qty', 0) for item in details)
            except:
                pass
        
        sales_by_day = {}
        for t in transactions:
            date_key = t['transaction_date'].strftime('%d/%m') if isinstance(t['transaction_date'], datetime) else t['transaction_date'][:10]
            sales_by_day[date_key] = sales_by_day.get(date_key, 0) + t['total_amount']
        
        transaction_types = {'biasa': 0, 'lelang': 0}
        for t in transactions:
            transaction_types[t['transaction_type']] += 1
        
        product_sales = {}
        for t in transactions:
            try:
                details = json.loads(t['details'])
                for item in details:
                    product_key = item.get('name', f"SKU:{item.get('sku')}")
                    if product_key not in product_sales:
                        product_sales[product_key] = {'sold': 0, 'revenue': 0}
                    product_sales[product_key]['sold'] += item.get('qty', 0)
                    product_sales[product_key]['revenue'] += item.get('subtotal', 0)
            except:
                pass
        
        top_products = sorted(
            [{'name': k, 'sold': v['sold'], 'revenue': v['revenue']} 
             for k, v in product_sales.items()],
            key=lambda x: x['sold'],
            reverse=True
        )[:5]
        
        recent_transactions = []
        for t in transactions[:10]:
            time_ago = get_time_ago(t['transaction_date'])
            recent_transactions.append({
                'transaction_id': t['transaction_id'],
                'username': t['username'],
                'total_amount': t['total_amount'],
                'time_ago': time_ago
            })
        
        stats = {
            'summary': {
                'total_revenue': float(total_revenue),
                'total_transactions': total_transactions,
                'avg_transaction': float(avg_transaction),
                'total_products_sold': total_products
            },
            'charts': {
                'sales_trend': {
                    'labels': list(sales_by_day.keys()),
                    'data': list(sales_by_day.values())
                },
                'transaction_types': {
                    'labels': ['Biasa', 'Lelang'],
                    'data': [transaction_types['biasa'], transaction_types['lelang']]
                }
            },
            'tables': {
                'top_products': top_products,
                'recent_transactions': recent_transactions
            }
        }
        
        return jsonify(stats)
        
    except Exception as e:
        print(f"Error getting stats: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        sys.close()

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

@app.route("/products")
def products():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return render_template('products.html', title='Daftar Produk')

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
    
    sys.close()
    
    return render_template('admin_history.html', 
                         title='History Transaksi',
                         transactions=transactions,
                         daily_summary=daily_summary,
                         date_filter=date_filter)

@app.route("/api/transaction/<int:transaction_id>")
def api_transaction_detail(transaction_id):
    if session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    
    sys = CashierSystem()
    cursor = sys.db.cursor(dictionary=True)
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
        sys.close()

@app.route("/admin/add", methods=['POST'])
def admin_add():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    sys = CashierSystem()
    sys.inventory.add_produk_baru(
        request.form.get('sku'),
        request.form.get('name'),
        request.form.get('harga'),
        request.form.get('expired_date')
    )
    sys.close()
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
    sys.close()
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
    sys.close()
    
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('admin'))

@app.route("/api/search_lelang")
def api_search_lelang():
    query = request.args.get('q', '')
    sys = CashierSystem()
    results = sys.inventory.search_produk_lelang(query)
    sys.close()
    return jsonify(results)

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
    sys.close()
    return jsonify({"success": success, "message": msg})

@app.route("/api/search")
def api_search():
    query = request.args.get('q', '')
    sys = CashierSystem()
    results = sys.inventory.search_produk(query)
    sys.close()
    return jsonify(results)

@app.route("/api/checkout", methods=['POST'])
def api_checkout():
    if not session.get('user_id'):
        return jsonify({"success": False, "message": "Silakan login terlebih dahulu"})
    
    data = request.json
    sys = CashierSystem()
    success, msg = sys.transaction.checkout(
        data['items'],
        session['user_id'],
        session['username']
    )
    sys.close()
    return jsonify({"success": success, "message": msg})

@app.route("/admin/history/monthly")
def admin_monthly_report():
    if session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 401
    
    year = request.args.get('year', datetime.now().year)
    month = request.args.get('month', datetime.now().month)
    
    sys = CashierSystem()
    report = sys.transaction.history.get_monthly_report(year, month)
    sys.close()
    
    return jsonify(report)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)