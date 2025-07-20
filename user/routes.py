from flask import session, redirect, url_for, render_template, request, flash
from app import app, db
from user.models import User
import uuid
from bson import ObjectId


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
    
@app.route('/user/login', methods=['POST'])
def login():
    from user.models import User
    user_model = User()
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
    return redirect(request.referrer or url_for('main'))

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    products = []
    total = 0
    for product_id, qty in cart.items():
        product = db.products.find_one({"_id": product_id})
        if product:
            product['qty'] = qty
            product['subtotal'] = product['price'] * qty
            total += product['subtotal']
            products.append(product)
    return render_template('cart.html', products=products, total=total)

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

@app.route('/admin/add_product', methods=['GET','POST'])
def add_product():
    if request.method == 'POST':
        product = {
            "_id": uuid.uuid4().hex,
            "name": request.form['name'],
            "price": float(request.form['price']),
            "stock": int(request.form['stock']),
            "description": request.form['description'],
            "image": request.form['image'],  # store image URL or filename
            "category": request.form.get('category')
        }
        db.products.insert_one(product)
        return redirect(url_for('main'))
    categories = list(db.categories.find())
    return render_template('add_product.html', categories=categories)

@app.route('/product/<product_id>')
def product_detail(product_id):
    product = db.products.find_one({"_id": product_id})
    if not product:
        return "Product not found", 404
    return render_template('products.html', product=product)

def is_admin():
    user = session.get('user')
    return user and user.get('email') == 'admin@shri.com'

@app.route('/admin/dashboard')
def admin_dashboard():
    if not is_admin():
        flash('Admin access required.')
        return redirect(url_for('main'))
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