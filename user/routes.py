from flask import session, redirect, url_for, render_template, request
from app import app, db
from user.models import User
import uuid

@app.route('/user/signup', methods=['POST'])
def signup():
    return User().signup()

@app.route('/user/signout')
def signout():
    return User().signout()
    
@app.route('/user/login', methods=['POST'])
def login():
    return User().login()

@app.route('/main')
def main():
    products = list(db.products.find())
    return render_template('main.html', products=products)

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

@app.route('/admin/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        product = {
            "_id": uuid.uuid4().hex,
            "name": request.form['name'],
            "price": float(request.form['price']),
            "stock": int(request.form['stock']),
            "description": request.form['description'],
            "image": request.form['image']  # store image URL or filename
        }
        db.products.insert_one(product)
        return redirect(url_for('main'))
    return render_template('add_product.html')

@app.route('/product/<product_id>')
def product_detail(product_id):
    product = db.products.find_one({"_id": product_id})
    if not product:
        return "Product not found", 404
    return render_template('products.html', product=product)