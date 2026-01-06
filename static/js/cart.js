// ============================================
// GLOBAL CART FUNCTIONS - PERBAIKAN
// ============================================

(function() {
    // Gunakan IIFE untuk menghindari global pollution
    let cartItems = [];
    let currentMode = 'biasa';
    
    // Initialize cart from localStorage
    function initCart() {
        try {
            const savedCart = JSON.parse(localStorage.getItem('cartItems') || '[]');
            cartItems = savedCart;
            console.log('[CART] Initialized with', cartItems.length, 'items');
        } catch (e) {
            console.error('[CART] Error initializing:', e);
            cartItems = [];
            localStorage.setItem('cartItems', JSON.stringify([]));
        }
    }
    
    // Save cart to localStorage
    function saveCart() {
        try {
            localStorage.setItem('cartItems', JSON.stringify(cartItems));
            console.log('[CART] Saved', cartItems.length, 'items');
        } catch (e) {
            console.error('[CART] Error saving:', e);
        }
    }
    
    // Universal addToCart function
    function addToCart(sku, name, price, mode = null) {
        console.log('[CART] Adding to cart:', { sku, name, price, mode });
        
        try {
            // Gunakan mode parameter jika ada, kalau tidak pakai currentMode
            const itemMode = mode || currentMode;
            
            // Parse price to float
            const itemPrice = parseFloat(price);
            if (isNaN(itemPrice)) {
                throw new Error('Harga tidak valid');
            }
            
            // Cek apakah item sudah ada di keranjang
            const existingItem = cartItems.find(item => 
                String(item.sku) === String(sku) && item.mode === itemMode
            );
            
            if (existingItem) {
                existingItem.qty += 1;
                existingItem.subtotal = existingItem.qty * existingItem.price;
                console.log('[CART] Updated existing item:', existingItem);
            } else {
                const newItem = {
                    sku: sku,
                    name: name,
                    price: itemPrice,
                    qty: 1,
                    subtotal: itemPrice,
                    mode: itemMode
                };
                cartItems.push(newItem);
                console.log('[CART] Added new item:', newItem);
            }
            
            // Save to localStorage
            saveCart();
            
            // Update cart display if on kasir page
            if (typeof updateCartDisplay === 'function') {
                updateCartDisplay();
            }
            
            // Show notification
            showCartNotification(`${name} ditambahkan ke keranjang`);
            
            return true;
            
        } catch (error) {
            console.error('[CART] Error adding to cart:', error);
            alert('❌ Gagal menambahkan ke keranjang: ' + error.message);
            return false;
        }
    }
    
    // Show cart notification
    function showCartNotification(message) {
        try {
            // Remove existing notification
            const existingNotif = document.querySelector('.cart-notification');
            if (existingNotif) {
                existingNotif.remove();
            }
            
            // Create new notification
            const notification = document.createElement('div');
            notification.className = 'cart-notification position-fixed top-0 end-0 m-3 p-3 bg-success text-white rounded shadow';
            notification.style.zIndex = '9999';
            notification.innerHTML = `
                <div class="d-flex align-items-center">
                    <i class="bi bi-check-circle me-2 fs-4"></i>
                    <div>
                        <strong>Berhasil!</strong>
                        <div class="small">${message}</div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(notification);
            
            // Auto remove after 3 seconds
            setTimeout(() => {
                notification.style.opacity = '0';
                notification.style.transition = 'opacity 0.5s';
                setTimeout(() => notification.remove(), 500);
            }, 3000);
        } catch (e) {
            console.error('[CART] Error showing notification:', e);
        }
    }
    
    // Get cart summary
    function getCartSummary() {
        const totalItems = cartItems.reduce((sum, item) => sum + item.qty, 0);
        const totalPrice = cartItems.reduce((sum, item) => sum + item.subtotal, 0);
        
        return {
            totalItems,
            totalPrice,
            items: [...cartItems] // Return copy
        };
    }
    
    // Clear cart
    function clearCart() {
        if (confirm('Yakin ingin mengosongkan keranjang?')) {
            cartItems = [];
            saveCart();
            
            if (typeof updateCartDisplay === 'function') {
                updateCartDisplay();
            }
            
            alert('✅ Keranjang berhasil dikosongkan!');
            return true;
        }
        return false;
    }
    
    // Set current mode
    function setCurrentMode(mode) {
        currentMode = mode;
    }
    
    // Check if cart is empty
    function isCartEmpty() {
        return cartItems.length === 0;
    }
    
    // Get cart items
    function getCartItems() {
        return [...cartItems]; // Return copy
    }
    
    // Update cart display function (untuk diakses dari luar)
    function updateCartDisplayFromCart() {
        if (typeof updateCartDisplay === 'function') {
            updateCartDisplay();
        }
    }
    
    window.Cart = {
        init: initCart,
        add: addToCart,
        getSummary: getCartSummary,
        clear: clearCart,
        isEmpty: isCartEmpty,
        setCurrentMode: setCurrentMode,
        items: getCartItems,
        updateDisplay: updateCartDisplayFromCart
    };
    

    initCart();
})();