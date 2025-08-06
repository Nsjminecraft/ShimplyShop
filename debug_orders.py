from flask import Blueprint, jsonify
from bson import ObjectId
from app import db

debug_bp = Blueprint('debug', __name__)

@debug_bp.route('/debug/orders')
def debug_orders():
    try:
        # Get all orders
        orders = list(db.orders.find({}))
        
        # Convert ObjectId to string for JSON serialization
        for order in orders:
            order['_id'] = str(order['_id'])
            if 'user_id' in order and isinstance(order['user_id'], ObjectId):
                order['user_id'] = str(order['user_id'])
        
        return jsonify({
            'status': 'success',
            'orders': orders
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
