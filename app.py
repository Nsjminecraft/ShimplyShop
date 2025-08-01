from flask import Flask, render_template, session, redirect, jsonify, request, url_for, flash
from functools import wraps
import pymongo
from pymongo import MongoClient
from gridfs import GridFS
import stripe
import os
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from flask_pymongo import PyMongo

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

# Configure MongoDB
app.config['MONGO_URI'] = os.getenv('MONGO_URI', 'mongodb://localhost:27017/ecommerce')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')

# Initialize MongoDB
mongo = PyMongo()
mongo.init_app(app)

# Initialize direct MongoDB client
try:
    client = pymongo.MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'))
    db = client['ecommerce']
    fs = GridFS(db)
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    raise

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
@app.route('/shipping-info')
@login_required
def shipping_info():
    # Check if cart is not empty
    user_id = str(session['user']['_id'])
    cart = mongo.db.carts.find_one({'user_id': user_id})
    
    if not cart or 'items' not in cart or not cart['items']:
        flash('Your cart is empty', 'error')
        return redirect(url_for('cart'))
    
    return render_template('checkout/shipping_info.html')

@app.route('/process-shipping', methods=['POST'])
@login_required
def process_shipping():
    # Save shipping info to session
    shipping_info = {
        'name': request.form.get('name'),
        'email': request.form.get('email'),
        'phone': request.form.get('phone'),
        'address': {
            'line1': request.form.get('line1'),
            'line2': request.form.get('line2', ''),
            'city': request.form.get('city'),
            'state': request.form.get('state'),
            'postal_code': request.form.get('postal_code'),
            'country': request.form.get('country')
        }
    }
    
    session['shipping_info'] = shipping_info
    return redirect(url_for('create_checkout_session'))

@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    try:
        cart = session.get('cart', {})
        if not cart:
            return jsonify({'error': 'Your cart is empty'}), 400
            
        line_items = []
        for product_id, quantity in cart.items():
            try:
                # First try to find the product with the exact ID
                product = db.products.find_one({'_id': product_id})
                
                # If not found and it looks like an ObjectId, try that
                if not product and ObjectId.is_valid(product_id):
                    product = db.products.find_one({'_id': ObjectId(product_id)})
                
                if product:
                    # Ensure price is a float and calculate in cents
                    price = float(product.get('price', 0)) * 100
                    if price <= 0:
                        continue
                        
                    line_items.append({
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': product.get('name', 'Product'),
                                'images': [product.get('image_url')] if product.get('image_url') else [],
                            },
                            'unit_amount': int(price),
                        },
                        'quantity': quantity,
                    })
            except Exception as e:
                app.logger.error(f"Error processing product {product_id}: {str(e)}", exc_info=True)
                continue
                
        if not line_items:
            return jsonify({'error': 'No valid items in cart'}), 400
            
        user_id = session['user'].get('_id', 'guest')
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=url_for('success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('cart', _external=True),
            metadata={
                'user_id': str(user_id),
                'total_amount': str(sum(item['price_data']['unit_amount'] * item['quantity'] for item in line_items) / 100),
                'item_count': str(len(cart))
            },
            shipping_address_collection={
                'allowed_countries': ['US', 'CA', 'GB', 'IN'],
            },
            phone_number_collection={
                'enabled': True,
            },
        )
        
        return jsonify({'id': checkout_session.id})
        
    except Exception as e:
        app.logger.error(f"Error in create_checkout_session: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/debug/session/<session_id>')
@login_required
def debug_session(session_id):
    """Debug endpoint to view raw Stripe session data"""
    if not session_id or session_id == 'undefined':
        return "No session ID provided"
        
    try:
        checkout_session = stripe.checkout.Session.retrieve(
            session_id,
            expand=['line_items', 'customer', 'shipping']
        )
        return jsonify({
            'success': True,
            'session': {
                'id': checkout_session.id,
                'shipping': getattr(checkout_session, 'shipping', None),
                'customer_details': getattr(checkout_session, 'customer_details', None),
                'shipping_address': getattr(checkout_session.shipping, 'address', None) if hasattr(checkout_session, 'shipping') else None,
                'shipping_name': getattr(checkout_session.shipping, 'name', None) if hasattr(checkout_session, 'shipping') else None
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
@app.route('/success')
@login_required
def success():
    from datetime import datetime  # Import datetime here to avoid circular imports
    
    session_id = request.args.get('session_id')
    if not session_id:
        flash('No session ID provided', 'error')
        return redirect(url_for('cart'))
    
    try:
        # Retrieve the session from Stripe with expanded line items and payment intent
        checkout_session = stripe.checkout.Session.retrieve(
            session_id,
            expand=['line_items', 'payment_intent']
        )
        
        # Get user email from session or checkout session
        user_email = session.get('user', {}).get('email')
        if not user_email and hasattr(checkout_session, 'customer_details') and hasattr(checkout_session.customer_details, 'email'):
            user_email = checkout_session.customer_details.email
        
        # Get the order from the database or create a new one
        order = db.orders.find_one({'payment_intent': checkout_session.payment_intent})
        
        if not order and checkout_session.payment_status == 'paid':
            # Create a new order
            order = {
                'user_id': str(session.get('user', {}).get('_id', '')),
                'items': [],  # Initialize as empty list
                'total': float(checkout_session.amount_total) / 100,
                'status': 'completed',
                'payment_intent': checkout_session.payment_intent,
                'created_at': datetime.utcnow(),
                'shipping_info': {}
            }
            
            # Add shipping info if available
            if hasattr(checkout_session, 'shipping') and checkout_session.shipping:
                order['shipping_info'] = {
                    'name': getattr(checkout_session.shipping, 'name', ''),
                    'address': {
                        'line1': getattr(getattr(checkout_session.shipping, 'address', {}), 'line1', ''),
                        'line2': getattr(getattr(checkout_session.shipping, 'address', {}), 'line2', ''),
                        'city': getattr(getattr(checkout_session.shipping, 'address', {}), 'city', ''),
                        'state': getattr(getattr(checkout_session.shipping, 'address', {}), 'state', ''),
                        'postal_code': getattr(getattr(checkout_session.shipping, 'address', {}), 'postal_code', ''),
                        'country': getattr(getattr(checkout_session.shipping, 'address', {}), 'country', '')
                    },
                    'phone': getattr(checkout_session.customer_details, 'phone', '') if hasattr(checkout_session, 'customer_details') else ''
                }
            
            # Add items to the order
            try:
                line_items = stripe.checkout.Session.list_line_items(session_id)
                order_items = []  # Create a new list for items
                for item in line_items.data:
                    order_items.append({
                        'product_id': getattr(getattr(item, 'price', {}), 'product', 'unknown'),
                        'name': getattr(item, 'description', 'Unknown Product'),
                        'price': float(getattr(item, 'amount_total', 0)) / 100,
                        'quantity': getattr(item, 'quantity', 1)
                    })
                order['items'] = order_items  # Assign the list to order['items']
                
            except Exception as e:
                app.logger.error(f"Error processing line items: {str(e)}", exc_info=True)
                flash('There was an error processing your order items. Please contact support.', 'error')
                return redirect(url_for('cart'))
            
            # Save the order to the database
            try:
                result = db.orders.insert_one(order)
                order['_id'] = str(result.inserted_id)  # Add string ID for template
            except Exception as e:
                app.logger.error(f"Error saving order to database: {str(e)}", exc_info=True)
                flash('There was an error saving your order. Please contact support.', 'error')
                return redirect(url_for('cart'))
        
        # If order was retrieved from DB, ensure proper dictionary structure
        if order:
            # Convert MongoDB document to a regular dictionary if it's a pymongo.cursor.Cursor
            if hasattr(order, 'items'):
                order = dict(order)
            
            # Ensure _id is a string
            if '_id' in order:
                order['_id'] = str(order['_id'])
                
            # Ensure items is a list
            if 'items' not in order or not isinstance(order['items'], list):
                order['items'] = []
            
            # Ensure shipping_info exists and is a dict
            if 'shipping_info' not in order or not isinstance(order['shipping_info'], dict):
                order['shipping_info'] = {}
            
            # Ensure total is a float
            if 'total' not in order:
                order['total'] = 0.0
            else:
                try:
                    order['total'] = float(order['total'])
                except (TypeError, ValueError):
                    order['total'] = 0.0
        
        # Clear the cart
        if 'cart' in session:
            del session['cart']
        
        if not order:
            flash('Order not found or could not be created', 'error')
            return redirect(url_for('cart'))
            
        # Create a safe copy of the order for the template
        safe_order = {
            '_id': order.get('_id'),
            'items': [
                {
                    'name': item.get('name', 'Unknown Item'),
                    'price': float(item.get('price', 0)),
                    'quantity': int(item.get('quantity', 1))
                } for item in order.get('items', [])
            ],
            'total': float(order.get('total', 0)),
            'shipping_info': order.get('shipping_info', {})
        }
            
        return render_template('success.html',
                            order=safe_order,
                            user_email=user_email)
        
    except Exception as e:
        app.logger.error(f"Error in success route: {str(e)}", exc_info=True)
        flash('An error occurred while processing your order. Please contact support with this reference: ' + (session_id or 'N/A'), 'error')
        return redirect(url_for('cart'))

@app.route('/cancel')
def cancel():
    return render_template('cancel.html')

@app.route('/')
def index():
    return render_template('landing.html')

@app.route('/test/cart')
def test_cart():
    """Test route to debug cart functionality"""
    # Clear any existing cart
    if 'cart' in session:
        session.pop('cart')
    
    # Add some test products to the database if they don't exist
    test_products = [
        {'_id': 'test1', 'name': 'Test Product 1', 'price': 9.99, 'description': 'Test product 1'},
        {'_id': 'test2', 'name': 'Test Product 2', 'price': 19.99, 'description': 'Test product 2'}
    ]
    
    # Insert test products if they don't exist
    for product in test_products:
        if not db.products.find_one({'_id': product['_id']}):
            db.products.insert_one(product)
    
    # Add test products to cart
    session['cart'] = {'test1': 2, 'test2': 1}
    session.modified = True
    
    return redirect(url_for('cart'))

if __name__ == "__main__":
    # Create session directory if it doesn't exist
    os.makedirs('/tmp/flask_session', exist_ok=True)
    app.run(host='0.0.0.0', port=8000, debug=True)
