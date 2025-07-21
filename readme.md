# ShimplyShop: E-commerce User Login & Shopping Cart System with Flask and MongoDB

A simple e-commerce web app built with Flask, MongoDB, and Passlib.  
Users can sign up, log in, browse products, add items to their cart, and log out. Passwords are securely hashed.

I KNOW IT SAYS RUPPES BUT I LIVE IN CANADA DONT WORRY ABOUT IT

## Features

- User registration (sign up)
- User login and logout
- Password hashing with PBKDF2 (Passlib)
- Session management
- MongoDB for user and product data storage
- Add/view products (admin)
- Product detail pages
- Shopping cart (add, view, remove items)

## Project Structure

```
commers/
├── run
├── app.py
├── user/
│   ├── __init__.py
│   ├── models.py
│   └── routes.py
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── main.html
│   ├── dashboard.html
│   ├── products.html
│   ├── cart.html
│   └── add_product.html
├── static/
│   ├── css/
│   │   ├── normalize.css
│   │   └── styles.css
│   ├── js/
│   │   ├── jquery.js
│   │   └── scripts.js
│   └── img/
│       └── ... (product/category images)
└── README.md
```

## Setup Instructions

1. **Clone the repository:**
    ```bash
    git clone <repo-url>
    cd commers
    ```

2. **Create and activate a virtual environment:**
    ```bash
    python3 -m venv env
    source env/bin/activate
    ```

3. **Install dependencies:**
    ```bash
    pip install flask pymongo passlib
    ```

4. **Start MongoDB:**
    - Make sure MongoDB is running on `localhost:27017`.

5. **Run the application:**
    ```bash
    sudo chmod +x run
    ./run
    ```
    or by Flask:
    ```bash
    python app.py
    ```

6. **Open your browser:**
    - Visit [http://localhost:8000](http://localhost:8000) or [http://localhost:5000](http://localhost:5000) (depending on your config).

## Usage

- **Sign Up:** Fill out the registration form on the home page.
- **Login:** Use your credentials to log in.
- **Browse Products:** Go to the main page to see categories and trending products.
- **Product Details:** Click a product to view its details.
- **Add to Cart:** Click "Add to Cart" on any product.
- **View Cart:** Click "Cart" in the header dropdown to see your cart, update, or remove items.
- **Dashboard:** View your user info and sign out.
- **Admin:** Go to `/admin/add_product` to add new products (for development/demo).

## Notes

- Passwords are hashed using PBKDF2 via Passlib.
- User sessions and cart are managed with Flask's session.
- Product images are referenced by URL or static path.
- Make sure to keep your `app.secret_key` secure in production.

## License

MIT License
