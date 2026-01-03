import os
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont

def generate_barcode_image(sku, product_name, price, output_folder="barcodes"):
    """
    Generate barcode label untuk produk
    """
    # Buat folder jika belum ada
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Gunakan Code128 format
    code128 = barcode.get_barcode_class('code128')
    
    # Generate barcode
    barcode_instance = code128(str(sku), writer=ImageWriter())
    
    # Save barcode image
    filename = f"{output_folder}/barcode_{sku}"
    barcode_instance.save(filename)
    
    # Add label text ke barcode
    add_label_to_barcode(filename, sku, product_name, price)
    
    print(f"✓ Barcode berhasil dibuat: {filename}.png")
    return f"{filename}.png"

def add_label_to_barcode(filename, sku, product_name, price):
    """
    Tambahkan teks label ke gambar barcode
    """
    # Buka gambar barcode
    img = Image.open(f"{filename}.png")
    
    # Buat gambar baru dengan ruang untuk label
    new_height = img.height + 100
    new_img = Image.new('RGB', (img.width, new_height), 'white')
    
    # Tempel barcode
    new_img.paste(img, (0, 30))
    
    # Tambahkan teks
    draw = ImageDraw.Draw(new_img)
    
    # Gunakan font default atau arial
    try:
        font_large = ImageFont.truetype("arial.ttf", 16)
        font_medium = ImageFont.truetype("arial.ttf", 14)
        font_small = ImageFont.truetype("arial.ttf", 12)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Nama produk (dipotong jika terlalu panjang)
    product_display = product_name[:20] + "..." if len(product_name) > 20 else product_name
    draw.text((10, 5), product_display, fill='black', font=font_large)
    
    # SKU
    draw.text((10, img.height + 40), f"SKU: {sku}", fill='gray', font=font_medium)
    
    # Harga
    price_text = f"Rp{int(price):,}"
    price_width = draw.textlength(price_text, font=font_medium)
    draw.text((img.width - price_width - 10, img.height + 40), 
              price_text, fill='red', font=font_medium)
    
    # Save gambar baru
    new_img.save(f"{filename}_label.png")
    
    # Hapus file lama
    os.remove(f"{filename}.png")
    
    # Rename file
    os.rename(f"{filename}_label.png", f"{filename}.png")

def generate_barcodes_from_database():
    """
    Generate barcode untuk semua produk di database
    """
    from logic import Database
    
    db = Database.get_conn()
    if not db:
        print("✗ Database tidak terhubung")
        return
    
    cursor = db.cursor(dictionary=True)
    
    # Ambil semua produk biasa
    cursor.execute("SELECT no_SKU, Name_product, Price FROM produk_biasa")
    products = cursor.fetchall()
    
    print(f"📊 Menemukan {len(products)} produk biasa")
    
    for product in products:
        try:
            generate_barcode_image(
                product['no_SKU'],
                product['Name_product'],
                product['Price']
            )
        except Exception as e:
            print(f"✗ Error barcode untuk SKU {product['no_SKU']}: {e}")
    
    # Ambil produk lelang
    cursor.execute("SELECT no_SKU, Name_product, Price FROM produk_lelang")
    auction_products = cursor.fetchall()
    
    print(f"📊 Menemukan {len(auction_products)} produk lelang")
    
    for product in auction_products:
        try:
            generate_barcode_image(
                product['no_SKU'],
                product['Name_product'],
                product['Price'],
                "barcodes/lelang"
            )
        except Exception as e:
            print(f"✗ Error barcode untuk SKU {product['no_SKU']}: {e}")
    
    cursor.close()
    db.close()
    print("\n✅ Semua barcode berhasil digenerate!")

def print_barcode_labels():
    """
    Print barcode labels (butuh koneksi printer)
    """
    import subprocess
    import platform
    
    folder = "barcodes"
    if not os.path.exists(folder):
        print("✗ Folder barcodes tidak ditemukan")
        return
    
    # List semua file barcode
    barcode_files = [f for f in os.listdir(folder) if f.endswith('.png')]
    
    if not barcode_files:
        print("✗ Tidak ada file barcode ditemukan")
        return
    
    print(f"🖨️  Mencetak {len(barcode_files)} label barcode...")
    
    for filename in barcode_files:
        filepath = os.path.join(folder, filename)
        
        # Print berdasarkan OS
        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(filepath, "print")
            elif system == "Darwin":  # macOS
                subprocess.run(["lpr", filepath])
            elif system == "Linux":
                subprocess.run(["lp", filepath])
            
            print(f"✓ Mencetak: {filename}")
            
        except Exception as e:
            print(f"✗ Gagal print {filename}: {e}")

if __name__ == "__main__":
    print("🔷 BARCODE GENERATOR - JustCani")
    print("=" * 40)
    
    while True:
        print("\nPilih opsi:")
        print("1. Generate barcode untuk 1 produk")
        print("2. Generate barcode untuk semua produk di database")
        print("3. Print semua label barcode")
        print("4. Keluar")
        
        choice = input("\nPilihan (1/2/3/4): ").strip()
        
        if choice == '1':
            sku = input("Masukkan SKU: ").strip()
            name = input("Masukkan nama produk: ").strip()
            price = input("Masukkan harga: ").strip()
            
            try:
                price = float(price)
                generate_barcode_image(sku, name, price)
            except ValueError:
                print("✗ Harga harus angka!")
        
        elif choice == '2':
            generate_barcodes_from_database()
        
        elif choice == '3':
            print_barcode_labels()
        
        elif choice == '4':
            print("Keluar...")
            break
        
        else:
            print("✗ Pilihan tidak valid!")