#!/usr/bin/env python3
"""
Product Manager module.

This module contains the core business logic for managing products,
including CRUD operations, inventory management, and data validation.
"""

import uuid
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, validator

# Define Product data model
class Product(BaseModel):
    """
    Product data model.

    Attributes:
        product_id (str): Unique identifier for the product.
        name (str): Name of the product.
        description (str): Description of the product.
        price (float): Price of the product.
        inventory (int): Current inventory level of the product.
    """

    product_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    price: float
    inventory: int = 0

    # Validate price is positive
    @validator('price')
    def price_must_be_positive(cls, value):
        if value <= 0:
            raise ValueError('Price must be a positive value.')
        return value

# In-memory data store for products
products: Dict[str, Product] = {}

def create_product(product: Product) -> str:
    """
    Create a new product.

    Args:
        product (Product): Product data.

    Returns:
        str: Product ID of the newly created product.
    """
    products[product.product_id] = product
    return product.product_id

def get_product(product_id: str) -> Optional[Product]:
    """
    Get a product by ID.

    Args:
        product_id (str): ID of the product.

    Returns:
        Optional[Product]: Product data, or None if not found.
    """
    return products.get(product_id)

def update_product(product_id: str, updated_product: Product) -> Optional[Product]:
    """
    Update an existing product.

    Args:
        product_id (str): ID of the product to update.
        updated_product (Product): Updated product data.

    Returns:
        Optional[Product]: Updated product data, or None if not found.
    """
    if product_id in products:
        products[product_id] = updated_product
        return updated_product
    return None

def delete_product(product_id: str) -> bool:
    """
    Delete a product.

    Args:
        product_id (str): ID of the product to delete.

    Returns:
        bool: True if the product was deleted, False otherwise.
    """
    if product_id in products:
        del products[product_id]
        return True
    return False

def get_all_products() -> List[Product]:
    """
    Get a list of all products.

    Returns:
        List[Product]: List of all product data.
    """
    return list(products.values())

def update_product_inventory(product_id: str, quantity: int) -> Optional[Product]:
    """
    Update the inventory level of a product.

    Args:
        product_id (str): ID of the product.
        quantity (int): Quantity to add or remove from inventory.

    Returns:
        Optional[Product]: Updated product data, or None if not found.
    """
    product = get_product(product_id)
    if product:
        product.inventory += quantity
        products[product_id] = product
        return product
    return None