// ============================================
// KASIR PAGE FUNCTIONS
// ============================================

let currentMode = 'biasa';
let cartItems = [];

// Fungsi untuk set mode (biasa/lelang)
function setMode(mode) {
    currentMode = mode;
    document.getElementById('cartMode').textContent = mode === 'biasa' ? 'Biasa' : 'Lelang';
    
    // Update button styles
    document.getElementById('btnBiasa').className = mode === 'biasa' ? 'btn btn-primary' : 'btn btn-outline-primary';
    document.getElementById('btnLelang').className = mode === 'lelang' ? 'btn btn-warning' : 'btn btn-outline-warning';
    
    // Search ulang
    searchItem();
}

// Fungsi search produk
async function searchItem() {
    const query = document.getElementById('query').value;
    const resultsDiv = document.getElementById('searchResults');
    
    // Show loading
    resultsDiv.innerHTML = `
        <div class="col-12 text-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2 text-muted">Mencari produk...</p>
        </div>
    `;
    
    try {
        const endpoint = currentMode === 'biasa' ? '/api/search' : '/api/search_lelang';
        const response = await fetch(`${endpoint}?q=${encodeURIComponent(query)}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        // Handle error response
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Panggil fungsi displayResults
        displayResults(data);
        
    } catch (error) {
        console.error('Search error:', error);
        resultsDiv.innerHTML = `
            <div class="col-12 text-center py-5">
                <i class="bi bi-exclamation-triangle text-danger fs-1 d-block mb-2"></i>
                <p class="text-danger">Gagal memuat produk</p>
                <small class="text-muted">${error.message}</small>
            </div>
        `;
    }
}

// Fungsi untuk menampilkan hasil pencarian
function displayResults(products) {
    const resultsDiv = document.getElementById('searchResults');
    
    if (!products || products.length === 0) {
        resultsDiv.innerHTML = `
            <div class="col-12 text-center py-5">
                <i class="bi bi-search fs-1 text-muted d-block mb-2"></i>
                <p class="text-muted">Tidak ada produk ditemukan</p>
            </div>
        `;
        return;
    }
    
    resultsDiv.innerHTML = '';
    
    products.forEach(product => {
        const card = document.createElement('div');
        card.className = 'col-md-6 col-lg-4 mb-3';
        
        const expiredDate = product.expired_date ? 
            new Date(product.expired_date).toISOString().split('T')[0] : '-';
        
        card.innerHTML = `
            <div class="card h-100 border shadow-sm">
                <div class="card-body">
                    <h6 class="card-title fw-bold">${product.Name_product}</h6>
                    <p class="card-text small text-muted mb-1">
                        SKU: <span class="badge bg-secondary">${product.no_SKU}</span>
                    </p>
                    <p class="card-text mb-1">
                        <span class="fw-bold text-primary">Rp${parseInt(product.Price).toLocaleString()}</span>
                    </p>
                    ${currentMode === 'biasa' ? 
                        `<p class="card-text small">Stok: <span class="badge ${product.stok > 10 ? 'bg-success' : 'bg-warning'}">${product.stok} pcs</span></p>` : 
                        `<p class="card-text small text-warning"><i class="bi bi-tag"></i> Produk Lelang</p>`
                    }
                    <p class="card-text small text-muted">Exp: ${expiredDate}</p>
                    <button class="btn btn-sm btn-outline-primary w-100" 
                            onclick="addToCart(${product.no_SKU}, '${product.Name_product.replace(/'/g, "\\'")}', ${product.Price})">
                        <i class="bi bi-cart-plus"></i> Tambah
                    </button>
                </div>
            </div>
        `;
        
        resultsDiv.appendChild(card);
    });
}

// Fungsi tambah ke keranjang
function addToCart(sku, name, price) {
    // Cek apakah item sudah ada di keranjang
    const existingItem = cartItems.find(item => item.sku == sku && item.mode === currentMode);
    
    if (existingItem) {
        existingItem.qty += 1;
        existingItem.subtotal = existingItem.qty * price;
    } else {
        cartItems.push({
            sku: sku,
            name: name,
            price: price,
            qty: 1,
            subtotal: price,
            mode: currentMode
        });
    }
    
    updateCartDisplay();
}

// Update tampilan keranjang
function updateCartDisplay() {
    const cartList = document.getElementById('cartList');
    const cartCount = document.getElementById('cartCount');
    const totalHarga = document.getElementById('totalHarga');
    
    // Update count
    const totalItems = cartItems.reduce((sum, item) => sum + item.qty, 0);
    cartCount.textContent = `${totalItems} Item`;
    
    // Update cart list
    if (cartItems.length === 0) {
        cartList.innerHTML = '<div class="text-center text-muted py-5 bg-light rounded">Belum ada item</div>';
        totalHarga.textContent = 'Rp0';
        return;
    }
    
    let html = '';
    let total = 0;
    
    cartItems.forEach((item, index) => {
        total += item.subtotal;
        html += `
            <div class="cart-item border-bottom pb-2 mb-2">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="mb-1">${item.name}</h6>
                        <small class="text-muted">SKU: ${item.sku}</small>
                        <div class="mt-2">
                            <button class="btn btn-sm btn-outline-secondary btn-sm" onclick="updateQty(${index}, -1)">-</button>
                            <span class="mx-2">${item.qty} @Rp${parseInt(item.price).toLocaleString()}</span>
                            <button class="btn btn-sm btn-outline-secondary btn-sm" onclick="updateQty(${index}, 1)">+</button>
                            <button class="btn btn-sm btn-outline-danger btn-sm ms-2" onclick="removeFromCart(${index})">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </div>
                    <div class="text-end">
                        <h6 class="mb-0 text-primary">Rp${parseInt(item.subtotal).toLocaleString()}</h6>
                        ${item.mode === 'lelang' ? '<small class="text-warning"><i class="bi bi-tag"></i> Lelang</small>' : ''}
                    </div>
                </div>
            </div>
        `;
    });
    
    cartList.innerHTML = html;
    totalHarga.textContent = `Rp${parseInt(total).toLocaleString()}`;
    
    // Show/hide lelang info
    const hasLelang = cartItems.some(item => item.mode === 'lelang');
    document.getElementById('lelangInfo').classList.toggle('d-none', !hasLelang);
}

// Fungsi update quantity
function updateQty(index, change) {
    const item = cartItems[index];
    const newQty = item.qty + change;
    
    if (newQty < 1) {
        removeFromCart(index);
        return;
    }
    
    item.qty = newQty;
    item.subtotal = item.qty * item.price;
    updateCartDisplay();
}

// Fungsi hapus dari keranjang
function removeFromCart(index) {
    cartItems.splice(index, 1);
    updateCartDisplay();
}

// Fungsi checkout
async function checkout() {
    if (cartItems.length === 0) {
        alert('Keranjang kosong!');
        return;
    }
    
    // Pisahkan item biasa dan lelang
    const biasaItems = cartItems.filter(item => item.mode === 'biasa');
    const lelangItems = cartItems.filter(item => item.mode === 'lelang');
    
    try {
        // Show loading
        document.getElementById('loadingSpinner').style.display = 'block';
        
        if (biasaItems.length > 0) {
            const response = await fetch('/api/checkout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    items: biasaItems.map(item => ({
                        sku: item.sku,
                        qty: item.qty
                    }))
                })
            });
            
            const result = await response.json();
            if (!result.success) {
                throw new Error(result.message);
            }
        }
        
        if (lelangItems.length > 0) {
            const response = await fetch('/api/checkout_lelang', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    items: lelangItems.map(item => ({
                        sku: item.sku,
                        qty: item.qty
                    }))
                })
            });
            
            const result = await response.json();
            if (!result.success) {
                throw new Error(result.message);
            }
        }
        
        // Reset cart
        cartItems = [];
        updateCartDisplay();
        document.getElementById('query').value = '';
        searchItem();
        
        alert('Transaksi berhasil!');
        
    } catch (error) {
        alert('Error: ' + error.message);
    } finally {
        document.getElementById('loadingSpinner').style.display = 'none';
    }
}

// ============================================
// ADMIN BARCODE FUNCTIONS
// ============================================

// Load produk untuk dropdown barcode
async function loadProductsForBarcode() {
    try {
        const response = await fetch('/api/products/for_barcode');
        const data = await response.json();
        
        const select = document.getElementById('barcodeProductSelect');
        select.innerHTML = '<option value="">-- Pilih produk --</option>';
        
        if (data.success && data.products && data.products.length > 0) {
            data.products.forEach(product => {
                const option = document.createElement('option');
                option.value = product.sku;
                option.textContent = `${product.name} (SKU: ${product.sku}) - Rp${parseInt(product.price).toLocaleString()}`;
                option.dataset.product = JSON.stringify(product);
                select.appendChild(option);
            });
            console.log(`✅ Loaded ${data.products.length} products for barcode`);
        } else {
            console.warn('No products found for barcode');
        }
    } catch (error) {
        console.error('Error loading products for barcode:', error);
        alert('Gagal memuat daftar produk');
    }
}

// Update preview barcode
function updateBarcodePreview() {
    const select = document.getElementById('barcodeProductSelect');
    const selectedOption = select.options[select.selectedIndex];
    
    if (!selectedOption || !selectedOption.value) {
        document.getElementById('barcodePreviewArea').style.display = 'none';
        document.getElementById('printBtn').disabled = true;
        document.getElementById('downloadBtn').disabled = true;
        return;
    }
    
    try {
        const product = JSON.parse(selectedOption.dataset.product);
        document.getElementById('barcodeProductName').textContent = product.name;
        document.getElementById('barcodeProductSKU').textContent = `SKU: ${product.sku}`;
        document.getElementById('barcodePreviewArea').style.display = 'block';
    } catch (e) {
        console.error('Error parsing product data:', e);
    }
}

// Generate barcode
async function generateBarcode() {
    const select = document.getElementById('barcodeProductSelect');
    const sku = select.value;
    
    if (!sku) {
        alert('Pilih produk terlebih dahulu!');
        return;
    }
    
    try {
        const response = await fetch(`/api/barcode/${sku}`);
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('barcodeImage').src = data.barcode;
            document.getElementById('printBtn').disabled = false;
            document.getElementById('downloadBtn').disabled = false;
            alert('Barcode berhasil digenerate!');
        } else {
            alert('Error: ' + (data.message || 'Gagal generate barcode'));
        }
    } catch (error) {
        console.error('Error generating barcode:', error);
        alert('Gagal generate barcode');
    }
}

// Print barcode
function printBarcode() {
    const sku = document.getElementById('barcodeProductSelect').value;
    if (sku) {
        window.open(`/api/print_barcode/${sku}`, '_blank');
    }
}

// Download barcode
function downloadBarcode() {
    const sku = document.getElementById('barcodeProductSelect').value;
    if (sku) {
        window.open(`/api/barcode/${sku}/download`, '_blank');
    }
}

// Generate semua barcode
async function generateAllBarcodes() {
    if (!confirm('Generate barcode untuk semua produk yang belum punya barcode?')) {
        return;
    }
    
    try {
        const response = await fetch('/api/barcode/generate_all', {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            alert(`Berhasil generate ${data.generated} barcode dari ${data.total} produk`);
            loadProductsForBarcode(); // Refresh list
        } else {
            alert('Error: ' + data.error);
        }
    } catch (error) {
        console.error('Error generating all barcodes:', error);
        alert('Gagal generate semua barcode');
    }
}

// View all barcodes
function viewBarcodeList() {
    alert('Fitur ini akan menampilkan daftar semua barcode');
    // Implementasi sesuai kebutuhan
}

// Check barcode status
async function checkBarcodeStatus() {
    try {
        const response = await fetch('/api/barcode/status');
        const data = await response.json();
        
        if (data.success) {
            const status = data.status;
            alert(
                `Status Barcode:\n\n` +
                `Total Produk: ${status.total_products}\n` +
                `Sudah punya barcode: ${status.with_barcode}\n` +
                `Belum punya barcode: ${status.without_barcode}\n` +
                `Progress: ${status.progress_percentage}%`
            );
        }
    } catch (error) {
        console.error('Error checking barcode status:', error);
    }
}

// ============================================
// INITIALIZATION
// ============================================

// Initialize saat halaman load
document.addEventListener('DOMContentLoaded', function() {
    // Untuk halaman kasir
    if (document.getElementById('query')) {
        console.log('Initializing kasir page...');
    }
    
    // Untuk halaman admin
    if (document.getElementById('barcodeProductSelect')) {
        console.log('Initializing admin barcode functions...');
        loadProductsForBarcode();
    }
});