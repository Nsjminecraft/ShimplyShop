import os
import base64
from flask import session, redirect, url_for, render_template, request, flash, send_from_directory
from app import app, db
from user.models import User
import uuid
from bson import ObjectId, Binary
from bson.binary import Binary
import re
from werkzeug.utils import secure_filename
from gridfs import GridFS, NoFile
from io import BytesIO
from flask import send_file, abort
from pymongo import MongoClient
from gridfs import GridFS

# Initialize GridFS
fs = GridFS(db)

def get_image(image_id):
    try:
        # Try to get the file from GridFS
        grid_out = fs.get(ObjectId(image_id))
        return grid_out
    except NoFile:
        return None


@app.route('/user/signup', methods=['POST'])
def signup():
    from user.models import User
    user_model = User()
    result = user_model.signup(server_render=True)
    if isinstance(result, dict) and result.get('error'):
        return render_template('signup.html', signup_error=result['error'], login_error=None)
    return redirect('/main')

@app.route('/user/signout')
def signout():
    return User().signout()
    
@app.route('/user/login', methods=['GET', 'POST'])
def login():
    from user.models import User
    user_model = User()
    if request.method == 'GET':
        return render_template('login.html', signup_error=None, login_error=None)
    result = user_model.login(server_render=True)
    if isinstance(result, dict) and result.get('error'):
        return render_template('login.html', signup_error=None, login_error=result['error'])
    return redirect('/main')


@app.route('/main')
def main():
    products = list(db.products.find())
    categories = list(db.categories.find())
    return render_template('main.html', products=products, categories=categories)

@app.route('/add_to_cart/<product_id>', methods=['POST'])
def add_to_cart(product_id):
    cart = session.get('cart', {})
    cart[product_id] = cart.get(product_id, 0) + 1
    session['cart'] = cart
    product = db.products.find_one({'_id': product_id})
    product_name = product.get('name', 'Item') if product else 'Item'
    flash(f'{product_name} has been added to your cart!', 'success')
    return redirect(request.referrer or url_for('main'))

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    products = []
    total = 0
    for product_id, qty in cart.items():
        try:
            # Try to convert to ObjectId if it's a valid ObjectId string
            if isinstance(product_id, str) and ObjectId.is_valid(product_id):
                product = db.products.find_one({"_id": ObjectId(product_id)})
            else:
                product = db.products.find_one({"_id": product_id})
                
            if product:
                # Convert ObjectId to string for template
                product['_id'] = str(product['_id'])
                product['qty'] = qty
                product['subtotal'] = float(product['price']) * qty
                total += product['subtotal']
                products.append(product)
        except Exception as e:
            print(f"Error loading product {product_id}: {e}")
            continue
    
    # Get categories for the sidebar
    categories = list(db.categories.find())
    
    # Get Stripe public key from config
    from app import stripe_public_key  # Import from app.py
    
    return render_template('cart.html', 
                         products=products, 
                         total=total,
                         categories=categories,
                         stripe_public_key=stripe_public_key)

@app.route('/remove_from_cart/<product_id>', methods=['POST'])
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    if product_id in cart:
        del cart[product_id]
        session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/update_cart/<product_id>', methods=['POST'])
def update_cart(product_id):
    cart = session.get('cart', {})
    try:
        qty = int(request.form['qty'])
        if qty > 0:
            cart[product_id] = qty
        else:
            cart.pop(product_id, None)  # Remove if qty is set to 0 or less
        session['cart'] = cart
    except (ValueError, KeyError):
        pass  # Optionally flash an error message
    return redirect(url_for('cart'))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

def allowed_video_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'mp4', 'webm', 'ogg'}

def save_uploaded_file(file, file_type='image'):
    """Helper function to save uploaded file to GridFS"""
    if not file or file.filename == '':
        return None
        
    if file_type == 'image' and not allowed_file(file.filename):
        return None
    elif file_type == 'video' and not allowed_video_file(file.filename):
        return None
        
    filename = secure_filename(file.filename)
    file_id = fs.put(
        file,
        filename=filename,
        content_type=file.content_type
    )
    return str(file_id)

@app.route('/admin/add_product', methods=['GET','POST'])
def add_product():
    if request.method == 'POST':
        # Check if main image is provided
        if 'main_image' not in request.files:
            flash('Main image is required', 'error')
            return redirect(request.url)
            
        # Save main image
        main_image = request.files['main_image']
        main_image_id = save_uploaded_file(main_image)
        
        if not main_image_id:
            flash('Invalid main image. Please upload a valid image file (PNG, JPG, JPEG, GIF).', 'error')
            return redirect(request.url)
            
        # Save additional images
        additional_images = []
        for i in range(2, 4):  # For image2 and image3
            file_key = f'image{i}'
            if file_key in request.files:
                file = request.files[file_key]
                if file and file.filename != '':
                    file_id = save_uploaded_file(file)
                    if file_id:
                        additional_images.append({
                            'id': file_id,
                            'content_type': file.content_type
                        })
        
        # Save video if provided
        video_id = None
        video_content_type = None
        if 'video' in request.files:
            video = request.files['video']
            if video and video.filename != '':
                video_id = save_uploaded_file(video, file_type='video')
                if video_id:
                    video_content_type = video.content_type
        
        # Get form data
        name = request.form.get('name')
        price = float(request.form.get('price', 0))
        stock = int(request.form.get('stock', 0))
        description = request.form.get('description', '')
        category = request.form.get('category')
        
        # Create product document
        product = {
            "_id": str(uuid.uuid4()),
            "name": name,
            "price": price,
            "stock": stock,
            "description": description,
            "main_image": {
                'id': main_image_id,
                'content_type': main_image.content_type
            },
            "additional_images": additional_images,
            "video": {
                'id': video_id,
                'content_type': video_content_type
            } if video_id else None,
            "category": category
        }
        
        db.products.insert_one(product)
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    # GET request - show the form
    categories = list(db.categories.find())
    return render_template('add_product.html', categories=categories)

@app.route('/image/<image_id>')
def serve_image(image_id):
    if image_id == 'placeholder':
        # Serve the placeholder image
        return send_from_directory('static/img', 'placeholder.png')
    
    try:
        grid_out = fs.get(ObjectId(image_id))
        return send_file(
            BytesIO(grid_out.read()),
            mimetype=grid_out.content_type
        )
    except Exception as e:
        app.logger.error(f"Error serving image {image_id}: {str(e)}")
        abort(404)

@app.route('/video/<video_id>')
def serve_video(video_id):
    try:
        grid_out = fs.get(ObjectId(video_id))
        # Enable range requests for video streaming
        range_header = request.headers.get('Range', None)
        if not range_header:
            return send_file(
                BytesIO(grid_out.read()),
                mimetype=grid_out.content_type,
                as_attachment=False
            )
        
        # Handle range requests for video seeking
        size = grid_out.length
        byte1, byte2 = 0, None
        
        # Parse the range header
        range_header = range_header.replace('bytes=', '').split('-')
        if len(range_header) == 1:
            byte1 = int(range_header[0] if range_header[0] else 0)
        if len(range_header) > 1:
            byte1 = int(range_header[0] if range_header[0] else 0)
            byte2 = int(range_header[1]) if range_header[1] else size - 1
        
        length = size - byte1 if byte2 is None else (byte2 - byte1 + 1)
        
        grid_out.seek(byte1)
        data = grid_out.read(length)
        
        response = Response(
            data,
            206,  # Partial Content
            mimetype=grid_out.content_type,
            direct_passthrough=True,
            content_type=grid_out.content_type
        )
        
        response.headers.add('Content-Range', f'bytes {byte1}-{byte1 + len(data) - 1}/{size}')
        response.headers.add('Accept-Ranges', 'bytes')
        return response
        
    except Exception as e:
        app.logger.error(f"Error serving video {video_id}: {str(e)}")
        abort(404)


@app.route('/products')
def all_products():
    products = list(db.products.find())
    categories = list(db.categories.find())
    return render_template('all_products.html', products=products, categories=categories)

def is_admin():
    user = session.get('user')
    return user and user.get('email') == 'admin@shri.com'

@app.route('/admin/dashboard')
def admin_dashboard():
    if not is_admin():
        flash('Admin access required.')
        return redirect(url_for('main'))
    q = request.args.get('q', '').strip()
    if q:
        products = list(db.products.find({
            "$or": [
                {"name": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}}
            ]
        }))
    else:
        products = list(db.products.find())
    categories = list(db.categories.find()) if hasattr(db, 'categories') else []
    return render_template('admin_dashboard.html', products=products, categories=categories)

@app.route('/session/')
def show_session():
    return f"<pre>{dict(session)}</pre>"

@app.route('/admin/remove_product/<product_id>', methods=['POST'])
def remove_product(product_id):
    if not is_admin():
        flash('Admin access required.')
        return redirect(url_for('main'))
    db.products.delete_one({'_id': product_id})
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_category', methods=['POST'])
def add_category():
    if not is_admin():
        flash('Admin access required.')
        return redirect(url_for('main'))
    name = request.form.get('category_name')
    if name:
        db.categories.insert_one({'name': name})
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/remove_category/<category_id>', methods=['POST'])
def remove_category(category_id):
    if not is_admin():
        flash('Admin access required.')
        return redirect(url_for('main'))
    try:
        db.categories.delete_one({'_id': ObjectId(category_id)})
    except Exception:
        db.categories.delete_one({'_id': category_id})
    return redirect(url_for('admin_dashboard'))

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return redirect(url_for('main'))
    # Search products by name or description (case-insensitive)
    products = list(db.products.find({
        "$or": [
            {"name": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}}
        ]
    }))
    categories = list(db.categories.find({
        "name": {"$regex": query, "$options": "i"}
    }))
    return render_template('search_results.html', products=products, categories=categories, query=query)

@app.route('/category/<category_name>')
def category_page(category_name):
    # Normalize category name for matching (case-insensitive, spaces/dashes)
    def normalize(name):
        return re.sub(r'[-\s]+', '-', name.strip().lower())
    # Find the category by normalized name
    categories = list(db.categories.find())
    selected_category = None
    for cat in categories:
        if normalize(cat['name']) == category_name:
            selected_category = cat
            break
    if not selected_category:
        return "Category not found", 404
    # Find products in this category
    products = list(db.products.find({"category": selected_category['name']}))
    return render_template('category.html', category=selected_category, products=products, categories=categories)