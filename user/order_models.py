from bson import ObjectId
from datetime import datetime
from app import db

class Order:
    STATUS_CHOICES = [
        'Order Placed',
        'Order Confirmed',
        'Order Processing',
        'Shipped',
        'In Transit',
        'Out for Delivery',
        'Delivered',
        'Shipment Failed',
        'Canceled',
        'Pending',
        'Expected Delivery',
        'Failed Delivery'
    ]

    @staticmethod
    def create_order(user_id, items, total_amount, payment_intent_id, shipping_address=None, **kwargs):
        """
        Create a new order
        
        Args:
            user_id: ID of the user placing the order
            items: List of dicts with product_id, name, quantity, price
            total_amount: Total amount of the order
            payment_intent_id: Stripe payment intent ID
            shipping_address: Dictionary containing shipping information
            **kwargs: Additional fields
        """
        # Initialize shipping address if not provided
        if shipping_address is None:
            shipping_address = {}
            
        # If shipping info is passed as individual fields in kwargs, use those
        if not shipping_address and all(k in kwargs for k in ['shipping_name', 'shipping_line1', 'shipping_city']):
            shipping_address = {
                'name': kwargs.get('shipping_name', ''),
                'phone': kwargs.get('shipping_phone', ''),
                'email': kwargs.get('shipping_email', ''),
                'address': {
                    'line1': kwargs.get('shipping_line1', ''),
                    'line2': kwargs.get('shipping_line2', ''),
                    'city': kwargs.get('shipping_city', ''),
                    'state': kwargs.get('shipping_state', ''),
                    'postal_code': kwargs.get('shipping_postal_code', ''),
                    'country': kwargs.get('shipping_country', '')
                },
                'shipping_method': 'Standard Shipping'
            }
            
        # Ensure shipping_address has all required fields
        if 'address' not in shipping_address:
            shipping_address['address'] = {}
        if 'name' not in shipping_address:
            shipping_address['name'] = ''
        if 'phone' not in shipping_address:
            shipping_address['phone'] = ''
        if 'email' not in shipping_address:
            shipping_address['email'] = ''
        if 'shipping_method' not in shipping_address:
            shipping_address['shipping_method'] = 'Standard Shipping'
        
        order = {
            'user_id': user_id,
            'items': items,
            'total_amount': total_amount,
            'shipping_address': shipping_address,
            'status': 'Order Placed',
            'tracking_number': None,
            'payment_intent_id': payment_intent_id,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Add any additional fields that were passed in kwargs
        order.update(kwargs)
        
        result = db.orders.insert_one(order)
        return str(result.inserted_id)

    @staticmethod
    def get_user_orders(user_id):
        """
        Get all orders for a specific user
        Returns a list of order dictionaries with proper formatting
        """
        from flask import current_app
        orders = []
        
        try:
            # Try both string and ObjectId formats for user_id
            query_conditions = [{'user_id': user_id}]
            
            # Add ObjectId condition if the user_id is a valid ObjectId string
            try:
                if ObjectId.is_valid(str(user_id)):
                    query_conditions.append({'user_id': ObjectId(user_id)})
            except Exception:
                pass
                
            query = {'$or': query_conditions}
            
            # Get orders from database
            db_orders = list(db.orders.find(query).sort('created_at', -1))
            current_app.logger.debug(f'Found {len(db_orders)} orders for user {user_id}')
            
            for order in db_orders:
                try:
                    # Create a new dictionary for the formatted order
                    formatted_order = {}
                    
                    # Process each field in the order
                    for key, value in order.items():
                        if key == '_id':
                            formatted_order['_id'] = str(value)
                        elif key == 'user_id' and value:
                            formatted_order['user_id'] = str(value)
                        elif key == 'items':
                            # Ensure items is a list
                            if not isinstance(value, (list, tuple)):
                                value = list(value) if hasattr(value, '__iter__') and not isinstance(value, str) else []
                            
                            # Process each item in the items list
                            formatted_items = []
                            for item in value:
                                if isinstance(item, dict):
                                    # Ensure product_id is a string if it exists
                                    if 'product_id' in item and item['product_id'] is not None:
                                        item = item.copy()  # Don't modify the original
                                        item['product_id'] = str(item['product_id'])
                                    formatted_items.append(item)
                            
                            formatted_order['items'] = formatted_items
                        elif key in ['created_at', 'updated_at']:
                            if isinstance(value, datetime):
                                formatted_order[key] = value.isoformat()
                            else:
                                formatted_order[key] = str(value)
                        else:
                            formatted_order[key] = value
                    
                    # Ensure all required fields exist
                    if 'items' not in formatted_order:
                        formatted_order['items'] = []
                    if 'status' not in formatted_order:
                        formatted_order['status'] = 'Pending'
                    
                    orders.append(formatted_order)
                    
                except Exception as e:
                    order_id = str(order.get('_id', 'unknown'))
                    current_app.logger.error(f'Error formatting order {order_id}: {str(e)}', exc_info=True)
                    continue
                    
        except Exception as e:
            current_app.logger.error(f'Error in get_user_orders for user {user_id}: {str(e)}', exc_info=True)
            
        current_app.logger.debug(f'Returning {len(orders)} formatted orders')
        return orders
        
        return orders

    @staticmethod
    def get_all_orders():
        """
        Get all orders (admin only)
        Returns a list of order dictionaries with proper formatting
        """
        orders = []
        for order in db.orders.find().sort('created_at', -1):
            # Convert _id to string and ensure items is a list
            order['_id'] = str(order['_id'])
            if 'items' not in order:
                order['items'] = []
            elif not isinstance(order['items'], list):
                order['items'] = list(order['items'])
            
            # Ensure user_id is a string
            if 'user_id' in order and order['user_id']:
                order['user_id'] = str(order['user_id'])
            
            # Ensure timestamps are strings
            for time_field in ['created_at', 'updated_at']:
                if time_field in order and isinstance(order[time_field], datetime):
                    order[time_field] = order[time_field].isoformat()
            
            orders.append(order)
        
        return orders

    @staticmethod
    def get_order_by_id(order_id):
        """
        Get a single order by ID with proper formatting
        """
        from flask import current_app
        
        try:
            if not ObjectId.is_valid(str(order_id)):
                current_app.logger.error(f'Invalid order ID format: {order_id}')
                return None
                
            order = db.orders.find_one({'_id': ObjectId(order_id)})
            if not order:
                current_app.logger.warning(f'Order not found: {order_id}')
                return None
                
            # Create a new dictionary for the formatted order
            formatted_order = {}
            
            # Process each field in the order
            for key, value in order.items():
                if key == '_id':
                    formatted_order['_id'] = str(value)
                elif key == 'user_id' and value:
                    formatted_order['user_id'] = str(value)
                elif key == 'items':
                    # Ensure items is a list
                    if not isinstance(value, (list, tuple)):
                        value = list(value) if hasattr(value, '__iter__') and not isinstance(value, str) else []
                    
                    # Process each item in the items list
                    formatted_items = []
                    for item in value:
                        if isinstance(item, dict):
                            # Ensure product_id is a string if it exists
                            if 'product_id' in item and item['product_id'] is not None:
                                item = item.copy()  # Don't modify the original
                                item['product_id'] = str(item['product_id'])
                            formatted_items.append(item)
                    
                    formatted_order['items'] = formatted_items
                elif key in ['created_at', 'updated_at']:
                    if isinstance(value, datetime):
                        formatted_order[key] = value.isoformat()
                    else:
                        formatted_order[key] = str(value)
                else:
                    formatted_order[key] = value
            
            # Ensure all required fields exist
            if 'items' not in formatted_order:
                formatted_order['items'] = []
            if 'status' not in formatted_order:
                formatted_order['status'] = 'Pending'
                
            current_app.logger.debug(f'Formatted order: {formatted_order}')
            return formatted_order
            
        except Exception as e:
            current_app.logger.error(f'Error in get_order_by_id for order {order_id}: {str(e)}', exc_info=True)
            return None

    @staticmethod
    def update_order_status(order_id, status, tracking_number=None):
        """
        Update order status (for admin)
        """
        from flask import current_app
        
        try:
            if status not in Order.STATUS_CHOICES:
                raise ValueError(f"Invalid status: {status}. Must be one of {Order.STATUS_CHOICES}")
                
            # Convert order_id to ObjectId if it's a string
            if isinstance(order_id, str):
                if not ObjectId.is_valid(order_id):
                    raise ValueError(f"Invalid order_id format: {order_id}")
                order_id = ObjectId(order_id)
                
            update_data = {
                'status': status,
                'updated_at': datetime.utcnow()
            }
            
            if tracking_number:
                update_data['tracking_number'] = tracking_number
                
            result = db.orders.update_one(
                {'_id': order_id},
                {'$set': update_data}
            )
            
            if result.matched_count == 0:
                current_app.logger.warning(f"No order found with id: {order_id}")
                return False
                
            current_app.logger.info(f"Updated order {order_id} status to {status}")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error updating order status: {str(e)}", exc_info=True)
            raise
