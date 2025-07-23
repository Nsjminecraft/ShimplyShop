# ShimplyShop: E-commerce User Login & Shopping Cart System with Flask and MongoDB

A feature-rich e-commerce web app built with Flask, MongoDB, and GridFS.  
Users can sign up, log in, browse products, add items to their cart, and log out. Admins can manage products and categories with image uploads.

I KNOW IT SAYS RUPPES BUT I LIVE IN CANADA DONT WORRY ABOUT IT


## 🌟 Features

- User registration (sign up) and authentication
- Secure password hashing with PBKDF2 (Passlib)
- Session management
- MongoDB with GridFS for data and image storage
- Product management (CRUD operations)
- Image upload and storage for products
- Category management
- Product search functionality
- Shopping cart with add/remove/update quantity
- Responsive design for all devices
- Admin dashboard for product and category management

## 🏗️ Project Structure

```
commers/
├── run                      # Application launcher
├── app.py                   # Main application setup and routes
├── user/
│   ├── __init__.py
│   ├── models.py           # Database models
│   └── routes.py           # All application routes
├── templates/
│   ├── base.html           # Base template
│   ├── home.html           # Home page
│   ├── main.html           # Main product listing
│   ├── dashboard.html      # Admin dashboard
│   ├── products.html       # Product detail page
│   ├── all_products.html   # All products listing
│   ├── cart.html           # Shopping cart
│   ├── add_product.html    # Add/edit product form
│   ├── login.html          # User login
│   ├── signup.html         # User registration
│   └── landing.html        # Landing page
├── static/
│   ├── css/
│   │   ├── normalize.css  # CSS reset
│   │   └── styles.css     # Main styles
│   └── img/               # Static images (logo, etc.)
└── README.md              # This file
```

## 🚀 Setup Instructions

### Prerequisites

- Python 3.8+
- MongoDB (local or Atlas)
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone [your-repo-url]
   cd commers
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: .\env\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   If you don't have a requirements.txt, install the required packages manually:
   ```bash
   pip install flask pymongo passlib gridfs werkzeug
   ```

4. **Configure the application**
   - Make sure MongoDB is running locally or update the connection string in `app.py`
   - Set up your secret key in `app.py`

5. **Run the application**
   ```bash
   ./run
   ```
   Or on Windows:
   ```
   python app.py
   ```

## 🖼️ Image Upload Feature

The application now supports image uploads for products using MongoDB GridFS:

- Supported formats: JPG, PNG, GIF
- Images are stored directly in MongoDB
- Automatic fallback to URL-based images for backward compatibility
- Responsive image display across all pages

## 🔧 Admin Features

1. **Add/Edit Products**
   - Upload product images
   - Set prices and stock
   - Categorize products

2. **Category Management**
   - Add/remove categories
   - Organize products by category

## 👥 User Features

- Create an account
- Browse products by category
- Search functionality
- Add products to cart
- Update cart quantities
- Secure checkout process

## 🔒 Security

- Password hashing with PBKDF2
- Secure session management
- CSRF protection
- Input validation

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- Built with Flask and MongoDB
- Uses GridFS for file storage
- Responsive design with CSS Grid and Flexbox

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
- **Add to Cart:** Click "Add to Cart" on any product.## License

MIT License

- **View Cart:** Click "Cart" in the header dropdown to see your cart, update, or remove items.
- **Dashboard:** View your user info and sign out.
- **Admin:** Go to `/admin/add_product` to add new products (for development/demo).

## Notes

- Passwords are hashed using PBKDF2 via Passlib.
- User sessions and cart are managed with Flask's session.
- Product images are referenced by URL or static path.
- Make sure to keep your `app.secret_key` secure in production.

