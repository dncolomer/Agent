#!/usr/bin/env python3
from flask import Blueprint, jsonify, request
from flask_restx import Api, Resource, fields
from src.services.order_service import OrderService

order_api = Blueprint('order_api', __name__)
api = Api(order_api, version='1.0', title='Order API', description='API for managing orders')

# Define data models
order_model = api.model('Order', {
    'id': fields.Integer(required=True, description='Order ID'),
    'customer_id': fields.Integer(required=True, description='Customer ID'),
    'items': fields.List(fields.Nested(api.model('OrderItem', {
        'product_id': fields.Integer(required=True, description='Product ID'),
        'quantity': fields.Integer(required=True, description='Quantity')
    }))),
    'total_price': fields.Float(required=True, description='Total order price'),
    'status': fields.String(required=True, description='Order status')
})

# Define routes and handlers
@api.route('/orders')
class OrderList(Resource):
    @api.marshal_with(order_model, as_list=True)
    def get(self):
        """Get all orders"""
        return OrderService.get_all_orders()

    @api.expect(order_model)
    @api.marshal_with(order_model)
    def post(self):
        """Create a new order"""
        order_data = request.get_json()
        return OrderService.create_order(order_data)

@api.route('/orders/<int:order_id>')
class Order(Resource):
    @api.marshal_with(order_model)
    def get(self, order_id):
        """Get an order by ID"""
        return OrderService.get_order(order_id)

    @api.expect(order_model)
    @api.marshal_with(order_model)
    def put(self, order_id):
        """Update an existing order"""
        order_data = request.get_json()
        return OrderService.update_order(order_id, order_data)

    @api.response(204, 'Order deleted')
    def delete(self, order_id):
        """Delete an order"""
        OrderService.delete_order(order_id)
        return '', 204