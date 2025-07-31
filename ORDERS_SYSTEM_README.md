# E-commerce Orders System

This document provides an overview of the orders system implemented for the e-commerce platform.

## Features

1. **User Order Management**
   - View order history
   - Track order status
   - View order details including items, quantities, and prices
   - View shipping information

2. **Admin Order Management**
   - View all orders
   - Update order status
   - Add/update tracking numbers
   - Filter and search orders

3. **Order Statuses**
   - Order Placed
   - Order Confirmed
   - Order Processing
   - Shipped
   - In Transit
   - Out for Delivery
   - Delivered
   - Shipment Failed
   - Canceled
   - Pending
   - Expected Delivery
   - Failed Delivery

## Setup Instructions

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Up Environment Variables**
   Create a `.env` file in the project root with the following variables:
   ```
   FLASK_APP=app.py
   FLASK_ENV=development
   FLASK_SECRET_KEY=your-secret-key
   STRIPE_SECRET_KEY=your-stripe-secret-key
   STRIPE_PUBLIC_KEY=your-stripe-public-key
   MONGODB_URI=mongodb://localhost:27017/your_database_name
   ADMIN_EMAIL=admin@example.com
   ADMIN_PASSWORD=admin123
   ```

3. **Initialize the Database**
   Run the database initialization script:
   ```bash
   python init_db.py
   ```
   This will:
   - Create necessary database indexes
   - Create an admin user (if one doesn't exist)
   - Set up the orders collection

4. **Run the Application**
   ```bash
   flask run
   ```

## Using the Orders System

### For Users
1. Log in to your account
2. Click on "Account" in the top right corner
3. Select "My Orders" to view your order history
4. Click on any order to view its details

### For Admins
1. Log in with an admin account
2. Click on "Account" in the top right corner
3. Select "Admin Dashboard"
4. You can now:
   - View all orders
   - Update order statuses
   - Add/update tracking numbers
   - View order details

## Database Schema

### Orders Collection
```javascript
{
  _id: ObjectId,
  user_id: String,          // ID of the user who placed the order
  items: [{
    product_id: String,     // ID of the product
    name: String,          // Product name at time of purchase
    price: Number,         // Price in cents
    quantity: Number       // Quantity ordered
  }],
  total_amount: Number,     // Total order amount in cents
  status: String,          // Current order status
  tracking_number: String,  // Optional tracking number
  payment_intent_id: String,// Stripe payment intent ID
  shipping_address: {
    name: String,
    line1: String,
    line2: String,
    city: String,
    state: String,
    postal_code: String,
    country: String
  },
  created_at: Date,         // When the order was placed
  updated_at: Date          // When the order was last updated
}
```

## API Endpoints

### User Endpoints
- `GET /user/orders` - View all orders for the current user
- `GET /user/order/<order_id>` - View details of a specific order

### Admin Endpoints
- `GET /user/admin/orders` - View all orders (admin only)
- `POST /user/admin/order/update_status` - Update order status (admin only)

## Styling

Order-related styles are located in `static/css/orders.css`.

## Testing

To test the orders system:

1. Place a test order through the checkout process
2. Log in as an admin to update the order status
3. Log in as the user to view the updated order status

## Troubleshooting

- If orders aren't appearing, check the MongoDB connection
- If status updates aren't working, ensure the admin user has the correct permissions
- Check the Flask application logs for any error messages

For any issues, please refer to the application logs or contact the development team.
