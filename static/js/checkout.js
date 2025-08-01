document.addEventListener('DOMContentLoaded', function() {
    const checkoutButton = document.getElementById('checkout-button');
    if (!checkoutButton) return;
    
    // Initialize Stripe with the public key from the window object
    if (!window.stripePublicKey) {
        console.error('Stripe public key not found');
        alert('Payment processing is currently unavailable. Please try again later.');
        return;
    }
    
    const stripe = Stripe(window.stripePublicKey);
    
    checkoutButton.addEventListener('click', async function() {
        // Disable the button to prevent multiple clicks
        checkoutButton.disabled = true;
        checkoutButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
        
        try {
            // Get cart items from the page
            const cartItems = [];
            const productRows = document.querySelectorAll('tr[data-product-id]');
            
            productRows.forEach(row => {
                const productId = row.getAttribute('data-product-id');
                const quantityInput = row.querySelector('.cart-qty-input');
                const quantity = quantityInput ? parseInt(quantityInput.value, 10) : 1;
                
                if (productId && !isNaN(quantity) && quantity > 0) {
                    cartItems.push({
                        id: productId,
                        quantity: quantity
                    });
                }
            });
            
            if (cartItems.length === 0) {
                throw new Error('Your cart is empty');
            }
            
            // Create checkout session
            const response = await fetch('/create-checkout-session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ items: cartItems })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to create checkout session');
            }
            
            const session = await response.json();
            
            // Redirect to Stripe Checkout
            const result = await stripe.redirectToCheckout({
                sessionId: session.id
            });
            
            if (result.error) {
                throw result.error;
            }
            
        } catch (error) {
            console.error('Error:', error);
            alert('Error: ' + (error.message || 'Could not initiate checkout'));
            
            // Re-enable the button
            checkoutButton.disabled = false;
            checkoutButton.innerHTML = '<i class="fas fa-credit-card me-2"></i>Proceed to Checkout';
        }
    });
});