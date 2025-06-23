#!/usr/bin/env python3
"""
Product Service Module

This module contains the main business logic for managing products,
including CRUD operations, inventory management, and product catalog functionality.
"""

import logging
from typing import List, Optional

from src.product.models import Product
from src.product.repositories import ProductRepository

logger = logging.getLogger(__name__)


class ProductService:
    """
    Service class for managing product-related operations.
    """

    def __init__(self, product_repository: ProductRepository):
        self.product_repository = product_repository

    def create_product(self, product_data: dict) -> Product:
        """
        Create a new product.

        Args:
            product_data (dict): The data for the new product.

        Returns:
            Product: The created product object.

        Raises:
            ValueError: If the product data is invalid.
        """
        product = Product(**product_data)
        return self.product_repository.create(product)

    def get_product(self, product_id: int) -> Optional[Product]:
        """
        Get a product by its ID.

        Args:
            product_id (int): The ID of the product.

        Returns:
            Optional[Product]: The product object, or None if not found.
        """
        return self.product_repository.get(product_id)

    def get_all_products(self) -> List[Product]:
        """
        Get all products.

        Returns:
            List[Product]: A list of all product objects.
        """
        return self.product_repository.get_all()

    def update_product(self, product_id: int, product_data: dict) -> Optional[Product]:
        """
        Update a product.

        Args:
            product_id (int): The ID of the product to update.
            product_data (dict): The updated data for the product.

        Returns:
            Optional[Product]: The updated product object, or None if not found.

        Raises:
            ValueError: If the product data is invalid.
        """
        product = self.get_product(product_id)
        if not product:
            return None

        product.update_from_dict(product_data)
        return self.product_repository.update(product)

    def delete_product(self, product_id: int) -> bool:
        """
        Delete a product.

        Args:
            product_id (int): The ID of the product to delete.

        Returns:
            bool: True if the product was deleted, False otherwise.
        """
        return self.product_repository.delete(product_id)

    def update_product_inventory(self, product_id: int, quantity: int) -> Optional[Product]:
        """
        Update the inventory quantity for a product.

        Args:
            product_id (int): The ID of the product.
            quantity (int): The new inventory quantity.

        Returns:
            Optional[Product]: The updated product object, or None if not found.

        Raises:
            ValueError: If the quantity is negative.
        """
        if quantity < 0:
            raise ValueError("Quantity cannot be negative.")

        product = self.get_product(product_id)
        if not product:
            return None

        product.inventory_quantity = quantity
        return self.product_repository.update(product)

    def get_product_catalog(self) -> List[dict]:
        """
        Get the product catalog.

        Returns:
            List[dict]: A list of dictionaries representing the product catalog.
        """
        products = self.get_all_products()
        return [product.to_dict() for product in products]