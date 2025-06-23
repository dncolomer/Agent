#!/usr/bin/env python3
"""
This module contains the data models and schemas for products, orders, and related entities,
ensuring data integrity and consistency across the application.
"""

from datetime import datetime
from pydantic import BaseModel, Field, validator

# Product Model
class Product(BaseModel):
    """
    Represents a product in the e-commerce platform.
    """
    id: int | None = None
    name: str
    description: str
    price: float
    stock: int
    category: str

    @validator('price')
    def validate_price(cls, value):
        """
        Validates that the price is a positive value.
        """
        if value <= 0:
            raise ValueError('Price must be a positive value.')
        return value

    @validator('stock')
    def validate_stock(cls, value):
        """
        Validates that the stock quantity is a non-negative value.
        """
        if value < 0:
            raise ValueError('Stock quantity must be a non-negative value.')
        return value

# Order Model
class Order(BaseModel):
    """
    Represents an order in the e-commerce platform.
    """
    id: int | None = None
    customer_name: str
    customer_email: str
    order_date: datetime = Field(default_factory=datetime.now)
    total_amount: float
    items: list[OrderItem] = []

    @validator('customer_email')
    def validate_email(cls, value):
        """
        Validates the email format.
        """
        if '@' not in value:
            raise ValueError('Invalid email format.')
        return value

    @validator('total_amount')
    def validate_total_amount(cls, value):
        """
        Validates that the total amount is a positive value.
        """
        if value <= 0:
            raise ValueError('Total amount must be a positive value.')
        return value

# Order Item Model
class OrderItem(BaseModel):
    """
    Represents an item in an order.
    """
    product_id: int
    quantity: int
    price: float

    @validator('quantity')
    def validate_quantity(cls, value):
        """
        Validates that the quantity is a positive value.
        """
        if value <= 0:
            raise ValueError('Quantity must be a positive value.')
        return value

    @validator('price')
    def validate_price(cls, value):
        """
        Validates that the price is a positive value.
        """
        if value <= 0:
            raise ValueError('Price must be a positive value.')
        return value