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

@app.route('/', methods=['GET'])
def landing():
    return render_template('landing.html')

@app.route('/dashboard/')
@login_required
def dashboard():
    return render_template('dashboard.html')

from bson.objectid import ObjectId
from bson.errors import InvalidId

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
def success():
    session_id = request.args.get('session_id')
    if not session_id:
        return redirect(url_for('dashboard'))
    
    try:
        # Verify the session was successful
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        return render_template('success.html', session=checkout_session)
    except Exception as e:
        return str(e), 400

@app.route('/cancel')
def cancel():
    return render_template('cancel.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=True)


