// VARIABLES
let cart = [];
let currentMode = 'biasa';

// SET MODE (BIASA/LELANG)
function setMode(mode) {
    currentMode = mode;
    
    // Update button styles
    const btnBiasa = document.getElementById('btnBiasa');
    const btnLelang = document.getElementById('btnLelang');
    
    if (mode === 'biasa') {
        btnBiasa.className = 'btn btn-primary';
        btnLelang.className = 'btn btn-outline-warning';
    } else {
        btnBiasa.className = 'btn btn-outline-primary';
        btnLelang.className = 'btn btn-warning';
    }
    
    // Update cart mode label
    const cartMode = document.getElementById('cartMode');
    cartMode.textContent = mode === 'biasa' ? 'Biasa' : 'Lelang';
    cartMode.className = mode === 'biasa' ? 'badge bg-info ms-2' : 'badge bg-warning ms-2';
    
    // Show/hide lelang info
    const lelangInfo = document.getElementById('lelangInfo');
    lelangInfo.className = mode === 'lelang' ? 'alert alert-warning mt-3' : 'alert alert-warning mt-3 d-none';
    
    // Clear search
    document.getElementById('searchResults').innerHTML = 
        '<div class="text-muted text-center py-5 w-100">' +
        '<i class="bi bi-box-seam fs-1 d-block mb-2"></i>' +
        'Silakan cari barang</div>';
    
    document.getElementById('query').value = '';
}

// SEARCH PRODUCTS
async function searchItem() {
    const query = document.getElementById('query').value;
    const resultsDiv = document.getElementById('searchResults');
    
    if (query.length < 1) {
        resultsDiv.innerHTML = '<div class="text-muted text-center p-3">Mulai mengetik untuk mencari...</div>';
        return;
    }

    try {
        const endpoint = currentMode === 'lelang' ? '/api/search_lelang' : '/api/search';
        const response = await fetch(endpoint + '?q=' + encodeURIComponent(query));
        const data = await response.json();

        let html = '';
        if (data.length === 0) {
            html = '<div class="text-danger text-center p-3">Barang tidak ditemukan.</div>';
        } else {
            data.forEach(p => {
                const badgeClass = currentMode === 'lelang' ? 'badge bg-warning' : 'badge bg-primary';
                const badgeText = currentMode === 'lelang' ? 'LELANG' : 'BIASA';
                const btnClass = currentMode === 'lelang' ? 'btn btn-warning' : 'btn btn-primary';
                const btnIcon = currentMode === 'lelang' ? 'bi-tag' : 'bi-plus-lg';
                const stokText = p.stok !== undefined ? '| Stok: ' + p.stok : '';
                
                // Escape quotes in product name
                const safeName = p.Name_product.replace(/'/g, "\\'").replace(/"/g, '\\"');
                
                html += '<div class="product-item p-3 mb-2 rounded d-flex justify-content-between align-items-center">' +
                        '<div>' +
                        '<span class="d-block fw-bold text-dark">' + p.Name_product + '</span>' +
                        '<small class="text-muted">SKU: ' + p.no_SKU + ' ' + stokText + 
                        '<span class="' + badgeClass + ' ms-2">' + badgeText + '</span></small>' +
                        '</div>' +
                        '<div class="text-end">' +
                        '<span class="d-block fw-bold ' + (currentMode === 'lelang' ? 'text-danger' : 'text-primary') + '">' +
                        'Rp' + parseInt(p.Price).toLocaleString() + '</span>' +
                        '<button class="btn ' + btnClass + ' btn-sm mt-1" ' +
                        'onclick="addToCart(\'' + p.no_SKU + '\', \'' + safeName + '\', ' + p.Price + ', ' + (p.stok || 0) + ')">' +
                        '<i class="bi ' + btnIcon + '"></i> Tambah</button>' +
                        '</div>' +
                        '</div>';
            });
        }
        resultsDiv.innerHTML = html;
    } catch (error) {
        console.error("Search Error:", error);
        resultsDiv.innerHTML = '<div class="text-danger text-center p-3">Error sistem.</div>';
    }
}

// ADD TO CART
function addToCart(sku, name, price, stock) {
    // Check stock for regular products
    if (currentMode === 'biasa' && stock <= 0) {
        alert("Stok barang ini kosong!");
        return;
    }
    
    // Find existing item in cart
    const existingIndex = cart.findIndex(item => item.sku === sku && item.mode === currentMode);
    
    if (existingIndex !== -1) {
        // Increase quantity if exists
        cart[existingIndex].qty += 1;
    } else {
        // Add new item
        cart.push({
            sku: sku,
            name: name,
            price: parseFloat(price),
            qty: 1,
            mode: currentMode,
            stock: stock
        });
    }
    
    renderCart();
}

// RENDER CART
function renderCart() {
    const cartList = document.getElementById('cartList');
    const totalDisplay = document.getElementById('totalHarga');
    const cartCount = document.getElementById('cartCount');
    
    let html = '';
    let total = 0;

    cart.forEach((item, index) => {
        const subtotal = item.price * item.qty;
        total += subtotal;
        
        const badgeClass = item.mode === 'lelang' ? 'badge bg-warning' : 'badge bg-info';
        const badgeText = item.mode === 'lelang' ? 'LELANG' : 'BIASA';
        
        html += '<div class="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom">' +
                '<div style="flex: 1;">' +
                '<span class="fw-bold d-block">' + item.name + '</span>' +
                '<div class="d-flex align-items-center">' +
                '<small class="text-muted">' + item.qty + ' x Rp' + item.price.toLocaleString() + '</small>' +
                '<span class="' + badgeClass + ' ms-2 small">' + badgeText + '</span>' +
                '</div>' +
                '</div>' +
                '<div class="text-end" style="min-width: 100px;">' +
                '<span class="d-block fw-bold ' + (item.mode === 'lelang' ? 'text-danger' : 'text-success') + '">' +
                'Rp' + subtotal.toLocaleString() + '</span>' +
                '<i class="bi bi-trash text-danger cursor-pointer" ' +
                'onclick="removeFromCart(' + index + ')" style="cursor:pointer" title="Hapus"></i>' +
                '</div>' +
                '</div>';
    });

    if (cart.length === 0) {
        cartList.innerHTML = '<div class="text-center text-muted py-5 bg-light rounded">Belum ada item</div>';
    } else {
        cartList.innerHTML = html;
    }
    
    totalDisplay.innerText = 'Rp' + total.toLocaleString();
    cartCount.innerText = cart.length + ' Item';
}

// REMOVE FROM CART
function removeFromCart(index) {
    if (index >= 0 && index < cart.length) {
        cart.splice(index, 1);
        renderCart();
    }
}

// CHECKOUT
async function checkout() {
    if (cart.length === 0) {
        alert("Keranjang masih kosong!");
        return;
    }

    // Check if mixed modes
    const modes = [];
    cart.forEach(item => {
        if (!modes.includes(item.mode)) {
            modes.push(item.mode);
        }
    });
    
    if (modes.length > 1) {
        if (!confirm("Keranjang berisi produk biasa dan lelang. Proses terpisah?")) return;
        
        // Process biasa first
        const cartBiasa = cart.filter(item => item.mode === 'biasa');
        if (cartBiasa.length > 0) {
            if (!confirm('Proses ' + cartBiasa.length + ' produk biasa terlebih dahulu?')) return;
            await processCheckout(cartBiasa, 'biasa');
        }
        
        // Process lelang
        const cartLelang = cart.filter(item => item.mode === 'lelang');
        if (cartLelang.length > 0) {
            if (!confirm('Lanjut proses ' + cartLelang.length + ' produk lelang?')) return;
            await processCheckout(cartLelang, 'lelang');
        }
        
    } else {
        // Single mode
        const mode = modes[0];
        const modeText = mode === 'lelang' ? 'lelang' : 'biasa';
        
        if (!confirm('Proses transaksi ' + modeText + ' sekarang?')) return;
        await processCheckout(cart, mode);
    }
}

// PROCESS CHECKOUT
async function processCheckout(itemsToCheckout, mode) {
    try {
        const endpoint = mode === 'lelang' ? '/api/checkout_lelang' : '/api/checkout';
        
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ items: itemsToCheckout })
        });

        const result = await response.json();
        if (result.success) {
            alert('✅ Transaksi ' + mode + ' Berhasil!\n' + result.message);
            
            // Remove processed items
            cart = cart.filter(item => !itemsToCheckout.includes(item));
            renderCart();
            
            // Reset search
            document.getElementById('query').value = "";
            document.getElementById('searchResults').innerHTML = 
                '<div class="text-muted text-center py-5 w-100">' +
                '<i class="bi bi-box-seam fs-1 d-block mb-2"></i>' +
                'Silakan cari barang</div>';
                
        } else {
            alert('❌ Gagal: ' + result.message);
        }
    } catch (error) {
        alert("❌ Error sistem! Coba lagi atau hubungi admin.");
        console.error("Checkout error:", error);
    }
}

// INITIAL SETUP
document.addEventListener('DOMContentLoaded', function() {
    // Initialize mode
    setMode('biasa');
});