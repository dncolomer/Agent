#!/usr/bin/env python3
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Product(Base):
    """
    Product model representing the product entity in the e-commerce platform.
    Attributes:
        id (int): Unique identifier for the product.
        name (str): Name of the product.
        description (str): Detailed description of the product.
        price (float): Price of the product.
        stock_level (int): Current stock level of the product.
    """
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1024), nullable=True)
    price = Column(Float, nullable=False)
    stock_level = Column(Integer, nullable=False)

    def __repr__(self):
        """
        Returns a string representation of the Product instance.
        """
        return f"<Product(id={self.id}, name='{self.name}', price={self.price}, stock_level={self.stock_level})>"

    def update_stock(self, quantity):
        """
        Updates the stock level of the product.
        
        Args:
            quantity (int): The quantity to adjust the stock level by.
        
        Raises:
            ValueError: If the resulting stock level would be negative.
        """
        if self.stock_level + quantity < 0:
            raise ValueError("Stock level cannot be negative.")
        self.stock_level += quantity

    def apply_discount(self, discount_percentage):
        """
        Applies a discount to the product price.
        
        Args:
            discount_percentage (float): The percentage discount to apply.
        
        Raises:
            ValueError: If the discount percentage is not between 0 and 100.
        """
        if not 0 <= discount_percentage <= 100:
            raise ValueError("Discount percentage must be between 0 and 100.")
        discount_amount = self.price * (discount_percentage / 100)
        self.price -= discount_amount