
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


// Function untuk test checkout
async function testCheckout() {
    try {
        const testItems = [{
            sku: "12345",
            qty: 1
        }];
        
        const response = await fetch('/api/debug_cart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                items: testItems,
                test: true
            })
        });
        
        const result = await response.json();
        console.log('Test result:', result);
        alert(`Test result: ${result.success ? 'SUCCESS' : 'FAILED'}\nMessage: ${result.message}`);
        
    } catch (error) {
        console.error('Test error:', error);
        alert('Test failed: ' + error.message);
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