from flask import Flask, render_template, session, redirect, jsonify, request, url_for
from functools import wraps
import pymongo
from pymongo import MongoClient
from gridfs import GridFS
import stripe
import os
from bson.objectid import ObjectId
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

# Stripe configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
stripe_public_key = os.getenv('STRIPE_PUBLIC_KEY')

# Add Stripe public key to app config
app.config['STRIPE_PUBLIC_KEY'] = stripe_public_key

# Database
client = pymongo.MongoClient('localhost', 27017)
db = client.user_login_system

#Decorators
def login_required(f):
    @wraps(f)
    def wrap(*arg, **kwargs):
        if 'logged_in' in session:
            return f(*arg, **kwargs)
        else:
            return redirect('/')
    return wrap


# Routes
from user import routes
from user.order_routes import order_bp as order_blueprint

# Register blueprints
app.register_blueprint(order_blueprint, url_prefix='/user')

# Add is_admin to user session
@app.context_processor
def inject_user():
    if 'user' in session:
        # Check if user is admin (you can modify this based on your user model)
        user = db.users.find_one({'_id': session['user']['_id']})
        if user and 'is_admin' in user and user['is_admin']:
            session['user']['is_admin'] = True
        else:
            session['user']['is_admin'] = False
    return {}

@app.route('/', methods=['GET'])
def landing():
    return render_template('landing.html')

@app.route('/dashboard/')
@login_required
def dashboard():
    return render_template('dashboard.html')

from bson.objectid import ObjectId
from bson.errors import InvalidId

# Import and initialize filters
from filters import init_app as init_filters
init_filters(app)

@app.route('/product/<product_id>')
@login_required
def product_detail(product_id):
    try:
        # Try to convert to ObjectId if it's a valid ObjectId string
        try:
            product = db.products.find_one({'_id': ObjectId(product_id)})
        except (InvalidId, TypeError):
            # If not a valid ObjectId, try searching as a string
            product = db.products.find_one({'_id': product_id})
            
        if not product:
            return "Product not found", 404
        
        # Ensure product has required fields with defaults
        product = dict(product)  # Convert to dict to make it mutable
        
        # Set default values for missing fields
        if 'main_image' not in product or not product['main_image']:
            product['main_image'] = {'id': 'placeholder', 'content_type': 'image/png'}
        
        if 'additional_images' not in product:
            product['additional_images'] = []
            
        if 'price' not in product:
            product['price'] = 0.0
            
        if 'description' not in product:
            product['description'] = 'No description available'
            
        return render_template('products.html', 
                             product=product,
                             stripe_public_key=stripe_public_key)
    except Exception as e:
        app.logger.error(f"Error fetching product {product_id}: {str(e)}")
        return "An error occurred while loading the product", 500

@app.route('/signup', methods=['GET'])
def signup_page():
    return render_template('signup.html', signup_error=None, login_error=None)

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html', signup_error=None, login_error=None)

# Stripe routes
@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        data = request.get_json()
        items = data.get('items', [])
        
        if not items:
            return jsonify({'error': 'No items in cart'}), 400
        
        line_items = []
        
        for item in items:
            product_id = item.get('id')
            quantity = item.get('quantity', 1)
            
            if not product_id:
                continue
                
            # Try to find product with ObjectId first, then try with string ID
            try:
                product = db.products.find_one({'_id': ObjectId(product_id)})
                if not product:
                    product = db.products.find_one({'_id': product_id})
            except (InvalidId, TypeError):
                # If not a valid ObjectId, try searching as a string
                product = db.products.find_one({'_id': product_id})
                
            if not product:
                continue  # Skip products that can't be found
                
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': product.get('name', 'Unnamed Product'),
                        'description': product.get('description', ''),
                    },
                    'unit_amount': int(float(product.get('price', 0)) * 100),  # Convert to cents
                },
                'quantity': quantity,
            })
        
        if not line_items:
            return jsonify({'error': 'No valid products found'}), 400
            
        # Create checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=url_for('success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('cart', _external=True),  # Return to cart if cancelled
        )
        
        return jsonify({'sessionId': session.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/success')
@login_required
def success():
    session_id = request.args.get('session_id')
    if not session_id:
        return redirect(url_for('dashboard'))
    
    try:
        # Verify the session was successful
        checkout_session = stripe.checkout.Session.retrieve(
            session_id,
            expand=['line_items', 'customer', 'shipping']
        )
        
        app.logger.info(f"Checkout session: {checkout_session}")
        
        # Check if this is a checkout session with line items
        if checkout_session.payment_status == 'paid' and checkout_session.mode == 'payment':
            # Get the cart items from the database
            cart = db.carts.find_one({'user_id': session['user']['_id']}) or {'items': []}
            
            # Prepare order items
            order_items = []
            total_amount = 0
            
            # Get line items directly from Stripe
            line_items = stripe.checkout.Session.list_line_items(session_id)
            
            if line_items and hasattr(line_items, 'data'):
                for item in line_items.data:
                    product_name = item.description or 'Unnamed Product'
                    price = item.amount_total  # in cents
                    quantity = item.quantity
                    
                    order_items.append({
                        'product_id': item.price.product if hasattr(item, 'price') and hasattr(item.price, 'product') else 'unknown',
                        'name': product_name,
                        'price': price,
                        'quantity': quantity
                    })
                    total_amount += price * quantity
            else:
                # Fallback to cart items if line items not available
                for item in cart.get('items', []):
                    product = db.products.find_one({'_id': ObjectId(item.get('product_id'))})
                    if product:
                        price = int(float(product.get('price', 0)) * 100)  # in cents
                        quantity = item.get('quantity', 1)
                        order_items.append({
                            'product_id': str(product['_id']),
                            'name': product.get('name', 'Unnamed Product'),
                            'price': price,
                            'quantity': quantity
                        })
                        total_amount += price * quantity
            
            # Create shipping address from checkout session
            shipping_address = {}
            if hasattr(checkout_session, 'shipping') and checkout_session.shipping:
                address = checkout_session.shipping.address
                shipping_address = {
                    'name': getattr(checkout_session.shipping, 'name', ''),
                    'line1': getattr(address, 'line1', ''),
                    'line2': getattr(address, 'line2', ''),
                    'city': getattr(address, 'city', ''),
                    'state': getattr(address, 'state', ''),
                    'postal_code': getattr(address, 'postal_code', ''),
                    'country': getattr(address, 'country', '')
                }
            
            # Create order in database
            from user.order_models import Order
            order_id = Order.create_order(
                user_id=session['user']['_id'],
                items=order_items,
                total_amount=total_amount,
                shipping_address=shipping_address,
                payment_intent_id=checkout_session.payment_intent
            )
            
            # Clear the user's cart after successful order
            if cart and 'items' in cart:
                db.carts.update_one(
                    {'user_id': session['user']['_id']},
                    {'$set': {'items': []}}
                )
            
            # Prepare simplified data for the success page
            success_data = {
                'id': checkout_session.id,
                'amount_total': checkout_session.amount_total / 100,  # Convert to dollars
                'payment_status': checkout_session.payment_status,
                'customer_details': {
                    'email': getattr(checkout_session, 'customer_email', 
                                  getattr(checkout_session.customer_details, 'email', '') 
                                  if hasattr(checkout_session, 'customer_details') else '')
                },
                'line_items': {
                    'data': [
                        {
                            'description': item.description or 'Unnamed Product',
                            'amount_total': item.amount_total / 100,  # Convert to dollars
                            'quantity': item.quantity
                        }
                        for item in line_items.data if hasattr(line_items, 'data')
                    ]
                }
            }
            
            return render_template('success.html', 
                                session=success_data,
                                order_id=order_id)
        
        return render_template('success.html', 
                            error="Order processing incomplete. Please check your orders or contact support.")
    
    except Exception as e:
        app.logger.error(f"Error in success route: {str(e)}", exc_info=True)
        return render_template('success.html', 
                            error=f"An error occurred while processing your order. Your payment was successful, but there was an issue processing your order. Please contact support with order ID: {session_id}")

@app.route('/cancel')
def cancel():
    return render_template('cancel.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=True)


