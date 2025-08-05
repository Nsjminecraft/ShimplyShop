from flask import Blueprint, render_template, jsonify, request, redirect, url_for, session, flash, current_app
from functools import wraps
from bson import ObjectId
from .order_models import Order
from app import db, login_required
import logging

order_bp = Blueprint('order', __name__)

def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        try:
            # Check if user is logged in
            if 'user' not in session:
                flash('Please log in to access this page', 'danger')
                return redirect(url_for('login_page'))
            
            # Get user ID from session
            user_data = session['user']
            user_id = user_data.get('_id')
            
            if not user_id:
                flash('Invalid user session', 'danger')
                return redirect(url_for('login_page'))
            
            # First try to find user by _id as is (could be string or ObjectId)
            user = None
            
            # Try direct match first
            user = db.users.find_one({'_id': user_id})
            
            # If not found and it looks like an ObjectId, try converting
            if not user and ObjectId.is_valid(str(user_id)):
                user = db.users.find_one({'_id': ObjectId(user_id)})
            
            # If still not found, try by email as fallback
            if not user and 'email' in user_data:
                user = db.users.find_one({'email': user_data['email']})
                if user:
                    # Update session with correct _id
                    session['user']['_id'] = str(user['_id'])
            
            # Check if user is admin
            if user and user.get('is_admin'):
                # Update session with fresh user data
                user['_id'] = str(user['_id'])  # Ensure _id is a string
                session['user'] = {**session['user'], **user}
                return f(*args, **kwargs)
            
            # If we get here, user is not an admin
            flash('Admin access required. Please log in with an administrator account.', 'danger')
            return redirect(url_for('dashboard'))
        except Exception as e:
            current_app.logger.error(f'Admin check failed: {str(e)}', exc_info=True)
            flash('An error occurred while verifying your access. Please try again.', 'danger')
            return redirect(url_for('dashboard'))
    return wrap

@order_bp.route('/order/<order_id>/print', methods=['GET'])
@admin_required
def print_invoice(order_id):
    try:
        if not ObjectId.is_valid(order_id):
            flash('Invalid order ID', 'danger')
            return redirect(url_for('order.admin_orders'))
        
        order = Order.get_order_by_id(order_id)
        if not order:
            flash('Order not found', 'danger')
            return redirect(url_for('order.admin_orders'))
        
        # Generate PDF using a library like ReportLab or WeasyPrint
        # For now, we'll just redirect to a PDF view
        return redirect(url_for('static', filename='pdf/invoice.pdf'))
    except Exception as e:
        current_app.logger.error(f'Error printing invoice: {str(e)}')
        flash('Error generating invoice', 'danger')
        return redirect(url_for('order.admin_orders'))

@order_bp.route('/order/<order_id>/export', methods=['GET'])
@admin_required
def export_pdf(order_id):
    try:
        if not ObjectId.is_valid(order_id):
            flash('Invalid order ID', 'danger')
            return redirect(url_for('order.admin_orders'))
        
        order = Order.get_order_by_id(order_id)
        if not order:
            flash('Order not found', 'danger')
            return redirect(url_for('order.admin_orders'))
        
        # Generate PDF using a library like ReportLab or WeasyPrint
        # For now, we'll just redirect to a PDF view
        return redirect(url_for('static', filename='pdf/order.pdf'))
    except Exception as e:
        current_app.logger.error(f'Error exporting PDF: {str(e)}')
        flash('Error exporting PDF', 'danger')
        return redirect(url_for('order.admin_orders'))

@order_bp.route('/order/<order_id>/cancel', methods=['POST'])
@admin_required
def cancel_order(order_id):
    try:
        if not ObjectId.is_valid(order_id):
            flash('Invalid order ID', 'danger')
            return redirect(url_for('order.admin_orders'))

        # Fetch the order directly from the database
        order = db.orders.find_one({'_id': ObjectId(order_id)})
        if not order:
            flash('Order not found', 'danger')
            return redirect(url_for('order.admin_orders'))

        # Delete the order from the database
        result = db.orders.delete_one({'_id': ObjectId(order_id)})

        if result.deleted_count > 0:
            flash('Order has been canceled', 'success')
        else:
            flash('Order cancellation failed', 'danger')

        return redirect(url_for('order.admin_orders'))
    except Exception as e:
        current_app.logger.error(f'Error canceling order: {str(e)}')
        flash('Error canceling order', 'danger')
        return redirect(url_for('order.admin_orders'))

@order_bp.route('/orders')
def my_orders():
    try:
        # Check if user is logged in
        if 'user' not in session:
            flash('Please log in to view your orders', 'danger')
            return redirect(url_for('login_page'))
        
        # Get user ID from session
        user_data = session['user']
        user_id = user_data.get('_id')
        
        if not user_id:
            current_app.logger.error('No user ID found in session')
            flash('Invalid user session. Please log in again.', 'danger')
            return redirect(url_for('login_page'))
        
        current_app.logger.info(f'Fetching orders for user: {user_id}')
        
        # Get orders with proper formatting from the model
        try:
            orders = Order.get_user_orders(user_id)
            if not isinstance(orders, list):
                current_app.logger.error(f'Expected orders to be a list, got {type(orders)}')
                orders = []
            
            current_app.logger.info(f'Retrieved {len(orders)} orders for user {user_id}')
            
            # Debug log first order structure
            if orders:
                current_app.logger.debug('First order structure:')
                current_app.logger.debug(f'Order ID: {orders[0].get("_id")}')
                current_app.logger.debug(f'Items type: {type(orders[0].get("items"))}')
                current_app.logger.debug(f'Items length: {len(orders[0].get("items", [])) if hasattr(orders[0].get("items"), "__len__") else "N/A"}')
                current_app.logger.debug(f'Items content: {orders[0].get("items")}')
                current_app.logger.debug(f'Created at: {orders[0].get("created_at")} (type: {type(orders[0].get("created_at"))})')
            
            return render_template('orders/my_orders.html', 
                                orders=orders,
                                status_choices=Order.STATUS_CHOICES)
            
        except Exception as e:
            current_app.logger.error(f'Error processing orders: {str(e)}', exc_info=True)
            flash('An error occurred while processing your orders. Please try again.', 'danger')
            return redirect(url_for('dashboard'))
    
    except Exception as e:
        current_app.logger.error(f'Unexpected error in my_orders: {str(e)}', exc_info=True)
        flash('An unexpected error occurred. Please try again later.', 'danger')
        return redirect(url_for('dashboard'))

@order_bp.route('/order/<order_id>')
def order_detail(order_id):
    try:
        # Check if user is logged in
        if 'user' not in session:
            flash('Please log in to view order details', 'danger')
            return redirect(url_for('login_page'))
        
        user_data = session['user']
        user_id = user_data.get('_id')
        is_admin = user_data.get('is_admin', False)
        
        if not user_id:
            current_app.logger.error('No user ID found in session')
            flash('Invalid user session. Please log in again.', 'danger')
            return redirect(url_for('login_page'))
        
        # Validate order_id format
        if not ObjectId.is_valid(order_id):
            current_app.logger.warning(f'Invalid order ID format: {order_id}')
            flash('Invalid order ID', 'danger')
            return redirect(url_for('order.my_orders'))
        
        current_app.logger.info(f'Fetching order details for order ID: {order_id}, user ID: {user_id}')
        
        try:
            # Debug: Log before getting order
            current_app.logger.debug(f'About to call Order.get_order_by_id with order_id: {order_id}')
            
            # Get the raw order from the database
            order = db.orders.find_one({'_id': ObjectId(order_id)})
            
            # Debug: Log the raw order from database
            current_app.logger.debug(f'Raw order from DB: {order}')
            
            # Debug: Log the shipping address specifically
            if 'shipping_address' in order:
                current_app.logger.debug(f'Raw shipping address: {order["shipping_address"]}')
            else:
                current_app.logger.debug('No shipping_address found in order')
            
            if not order:
                current_app.logger.warning(f'Order not found: {order_id}')
                flash('Order not found', 'danger')
                return redirect(url_for('order.my_orders'))
            
            # Format the order data
            formatted_order = {
                '_id': str(order.get('_id')),
                'user_id': str(order.get('user_id')),
                'status': order.get('status', 'Pending'),
                'total_amount': order.get('total', 0),  # Changed from total_amount to total
                'tracking_number': order.get('tracking_number'),
                'payment_intent_id': order.get('payment_intent_id'),
                'shipping_address': order.get('shipping_address', {}),
                'created_at': order.get('created_at'),
                'items': []
            }
            
            # Format items if they exist
            if 'items' in order and order['items'] is not None:
                # Ensure items is a list
                if not isinstance(order['items'], (list, tuple)):
                    order['items'] = list(order['items']) if hasattr(order['items'], '__iter__') and not isinstance(order['items'], str) else []
                
                formatted_items = []
                for item in order['items']:
                    if isinstance(item, dict):
                        formatted_item = {
                            'product_id': str(item.get('product_id', '')),
                            'name': item.get('name', 'Unknown Product'),
                            'price': float(item.get('price', 0)),
                            'quantity': int(item.get('quantity', 1)),
                            'image_url': item.get('image_url', '')
                        }
                        formatted_items.append(formatted_item)
                
                formatted_order['items'] = formatted_items
            
            # Log the formatted order for debugging
            current_app.logger.debug(f'Formatted order: {formatted_order}')
            current_app.logger.debug(f'Order loaded - ID: {order_id}, Status: {formatted_order.get("status")}, Items: {len(formatted_order.get("items", []))}')
            
            # Check if user is authorized to view this order
            if str(formatted_order.get('user_id')) != str(user_id) and not is_admin:
                current_app.logger.warning(f'Unauthorized access attempt to order {order_id} by user {user_id}')
                flash('You are not authorized to view this order', 'danger')
                return redirect(url_for('order.my_orders'))
            
            return render_template('orders/order_detail.html', 
                                order=formatted_order,
                                status_choices=Order.STATUS_CHOICES,
                                is_admin=is_admin)
            
        except Exception as e:
            current_app.logger.error(f'Error processing order {order_id}: {str(e)}', exc_info=True)
            flash('An error occurred while loading the order details. Please try again.', 'danger')
            return redirect(url_for('order.my_orders'))
    
    except Exception as e:
        current_app.logger.error(f'Unexpected error in order_detail: {str(e)}', exc_info=True)
        flash('An unexpected error occurred. Please try again later.', 'danger')
        return redirect(url_for('dashboard'))

# Admin routes
@order_bp.route('/debug/order/<order_id>')
@login_required
def debug_order(order_id):
    """Debug route to inspect order data"""
    try:
        from bson import ObjectId, json_util
        import json
        
        # Get the raw order from the database
        order = db.orders.find_one({'_id': ObjectId(order_id)})
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Get the user's order to check permissions
        user_id = session.get('user', {}).get('_id')
        is_admin = session.get('user', {}).get('is_admin', False)
        
        # Check if user is authorized to view this order
        if str(order.get('user_id')) != str(user_id) and not is_admin:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Convert the order to a dictionary and handle ObjectId serialization
        order_dict = json.loads(json_util.dumps(order))
        
        return jsonify({
            'success': True,
            'order': order_dict,
            'shipping_address_exists': 'shipping_address' in order,
            'shipping_address': order.get('shipping_address', {})
        })
    except Exception as e:
        return jsonify({'error': str(e), 'type': type(e).__name__}), 500

@order_bp.route('/admin/orders')
@admin_required
def admin_orders():
    try:
        current_app.logger.info('Fetching orders for admin...')
        db_orders = list(db.orders.find().sort('created_at', -1))
        current_app.logger.info(f'Found {len(db_orders)} orders in database')

        orders_list = []
        for order_data in db_orders:
            try:
                # Directly format the order items into a new list
                formatted_items = []
                if 'items' in order_data and isinstance(order_data['items'], list):
                    for item in order_data['items']:
                        if isinstance(item, dict):
                            formatted_items.append({
                                'product_id': str(item.get('product_id', '')),
                                'name': item.get('name', 'Unknown Product'),
                                'price': item.get('price', 0),
                                'quantity': item.get('quantity', 1),
                                'image_url': item.get('image_url', '')
                            })
                
                # Get shipping info if available
                shipping_info = order_data.get('shipping_info', {})
                shipping_email = order_data.get('email')  # Try to get email directly from order
                
                if not shipping_email and isinstance(shipping_info, dict):
                    shipping_email = shipping_info.get('email')
                
                # Create the formatted order dictionary
                formatted_order = {
                    '_id': str(order_data.get('_id')),
                    'user_id': str(order_data.get('user_id', '')),
                    'status': order_data.get('status', 'Pending'),
                    'total_amount': order_data.get('total_amount', 0),
                    'created_at': order_data.get('created_at'),
                    'tracking_number': order_data.get('tracking_number'),
                    'order_items': formatted_items,  # Use a different key to avoid conflicts
                    'shipping_info': {
                        'email': shipping_email,
                        'name': shipping_info.get('name', ''),
                        'phone': shipping_info.get('phone', '')
                    },
                    'email': shipping_email  # For backward compatibility
                }
                orders_list.append(formatted_order)

            except Exception as e:
                current_app.logger.error(f'Error formatting order {order_data.get("_id")}: {str(e)}', exc_info=True)
                continue

        # Get user data for all orders
        user_ids = [order['user_id'] for order in orders_list if order.get('user_id')]
        current_app.logger.info(f'Found user IDs in orders: {user_ids}')
        
        users = {}
        if user_ids:
            # Convert string IDs to ObjectId for the query
            user_object_ids = [ObjectId(uid) for uid in user_ids if ObjectId.is_valid(uid)]
            current_app.logger.info(f'Valid user IDs for query: {user_object_ids}')
            
            user_cursor = db.users.find({'_id': {'$in': user_object_ids}})
            users = {str(user['_id']): user for user in user_cursor}
            current_app.logger.info(f'Found {len(users)} users in database')

        # Add user info and format date for each order
        for order in orders_list:
            user_id = order.get('user_id')
            current_app.logger.info(f'Processing order {order.get("_id")} with user_id: {user_id}')
            
            user = users.get(str(user_id) if user_id else '', {})
            current_app.logger.info(f'Found user data: {user}')
            
            order['user_name'] = user.get('name', 'Guest')
            order['user_email'] = user.get('email', 'No email')
            current_app.logger.info(f'Order {order.get("_id")} - Name: {order["user_name"]}, Email: {order["user_email"]}')
            
            if isinstance(order.get('created_at'), str):
                try:
                    from datetime import datetime
                    order['created_at'] = datetime.fromisoformat(order['created_at'].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    pass
        
        # Format status choices as (value, label) pairs
        status_choices = [(status, status) for status in Order.STATUS_CHOICES]
        
        return render_template('admin/orders.html', 
                            orders=orders_list, 
                            status_choices=status_choices)

    except Exception as e:
        current_app.logger.error(f'Error in admin_orders: {str(e)}', exc_info=True)
        flash('An error occurred while loading orders. Please try again.', 'danger')
        return redirect(url_for('dashboard'))

@order_bp.route('/admin/order/update_status', methods=['POST'])
@admin_required
def update_order_status():
    current_app.logger.info('Update status request received')
    current_app.logger.info(f'Form data: {request.form}')
    current_app.logger.info(f'Headers: {dict(request.headers)}')
    
    order_id = request.form.get('order_id')
    status = request.form.get('status')
    tracking_number = request.form.get('tracking_number', '').strip() or None
    
    try:
        if not order_id or not status:
            error_msg = f'Missing order_id or status. Got order_id: {order_id}, status: {status}'
            current_app.logger.error(error_msg)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 400
            flash(error_msg, 'danger')
            return redirect(url_for('order.admin_orders'))
            
        current_app.logger.info(f'Attempting to update order {order_id} to status {status}')
        
        # Update the order status in the database
        success = Order.update_order_status(order_id, status, tracking_number)
        
        if not success:
            error_msg = f'Failed to update order {order_id}. Order not found or update failed.'
            current_app.logger.error(error_msg)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': error_msg}), 404
            flash(error_msg, 'danger')
            return redirect(url_for('order.admin_orders'))
            
        current_app.logger.info(f'Successfully updated order {order_id} to status {status}')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': 'Order status updated successfully',
                'status': status
            })
            
        flash('Order status updated successfully', 'success')
        return redirect(url_for('order.admin_orders'))
        
    except Exception as e:
        error_msg = f'Error updating order status: {str(e)}'
        current_app.logger.error(error_msg, exc_info=True)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': error_msg,
                'error_type': str(type(e).__name__)
            }), 500
            
        flash(error_msg, 'danger')
        return redirect(url_for('order.admin_orders'))
