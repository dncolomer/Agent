#!/usr/bin/env python3
"""
Product API module.

This module defines the API contract and routes for product-related operations,
acting as the interface between the product service and other microservices.
"""

from flask import Blueprint, jsonify, request
from werkzeug.exceptions import BadRequest, NotFound

from src.services.product_service import ProductService

product_api = Blueprint('product_api', __name__)
product_service = ProductService()

@product_api.route('/products', methods=['GET'])
def get_products():
    """
    Retrieve a list of all products.

    Returns:
        A JSON response containing a list of products.
    """
    products = product_service.get_all_products()
    return jsonify(products)

@product_api.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """
    Retrieve a specific product by ID.

    Args:
        product_id (int): The ID of the product to retrieve.

    Returns:
        A JSON response containing the requested product.

    Raises:
        NotFound: If the product with the given ID is not found.
    """
    try:
        product = product_service.get_product_by_id(product_id)
    except ValueError:
        raise NotFound(f'Product with ID {product_id} not found.')

    return jsonify(product)

@product_api.route('/products', methods=['POST'])
def create_product():
    """
    Create a new product.

    Returns:
        A JSON response containing the created product.

    Raises:
        BadRequest: If the request data is invalid or missing required fields.
    """
    try:
        product_data = request.get_json()
        product = product_service.create_product(product_data)
    except (ValueError, KeyError) as e:
        raise BadRequest(str(e))

    return jsonify(product), 201

@product_api.route('/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """
    Update an existing product.

    Args:
        product_id (int): The ID of the product to update.

    Returns:
        A JSON response containing the updated product.

    Raises:
        NotFound: If the product with the given ID is not found.
        BadRequest: If the request data is invalid or missing required fields.
    """
    try:
        product_data = request.get_json()
        product = product_service.update_product(product_id, product_data)
    except ValueError as e:
        raise BadRequest(str(e))
    except KeyError:
        raise NotFound(f'Product with ID {product_id} not found.')

    return jsonify(product)

@product_api.route('/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """
    Delete a product.

    Args:
        product_id (int): The ID of the product to delete.

    Returns:
        A JSON response indicating success or failure.

    Raises:
        NotFound: If the product with the given ID is not found.
    """
    try:
        product_service.delete_product(product_id)
    except KeyError:
        raise NotFound(f'Product with ID {product_id} not found.')

    return jsonify({'message': 'Product deleted successfully.'}), 200