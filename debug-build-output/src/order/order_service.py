#!/usr/bin/env python3
"""
Order Service Module

This module handles order processing, including creating new orders,
updating order statuses, and integrating with payment and shipping services.
"""

import logging
from typing import Dict, List

from src.order.models import Order, OrderStatus
from src.payment.payment_service import process_payment
from src.shipping.shipping_service import initiate_shipment

logger = logging.getLogger(__name__)


class OrderService:
    """
    Order Service class for managing order-related operations.
    """

    def __init__(self, order_repository):
        """
        Initialize the OrderService with a repository for persisting orders.

        Args:
            order_repository (OrderRepository): Repository for persisting orders.
        """
        self.order_repository = order_repository

    def create_order(self, user_id: str, items: List[Dict]) -> Order:
        """
        Create a new order for the given user and items.

        Args:
            user_id (str): ID of the user placing the order.
            items (List[Dict]): List of items in the order.

        Returns:
            Order: The newly created order.

        Raises:
            ValueError: If the items list is empty.
        """
        if not items:
            raise ValueError("Items list cannot be empty.")

        order = Order(user_id=user_id, items=items, status=OrderStatus.PENDING)
        order = self.order_repository.create(order)

        try:
            process_payment(order.id, order.total_amount)
            order.status = OrderStatus.PAYMENT_RECEIVED
        except Exception as e:
            logger.error(f"Payment failed for order {order.id}: {e}")
            order.status = OrderStatus.PAYMENT_FAILED

        order = self.order_repository.update(order)
        return order

    def update_order_status(self, order_id: str, new_status: OrderStatus):
        """
        Update the status of an existing order.

        Args:
            order_id (str): ID of the order to update.
            new_status (OrderStatus): New status for the order.

        Returns:
            Order: The updated order.

        Raises:
            ValueError: If the new status is invalid.
        """
        if new_status not in OrderStatus:
            raise ValueError(f"Invalid order status: {new_status}")

        order = self.order_repository.get(order_id)
        if not order:
            logger.warning(f"Order {order_id} not found.")
            return None

        order.status = new_status
        if new_status == OrderStatus.SHIPPED:
            try:
                initiate_shipment(order.id, order.shipping_address)
            except Exception as e:
                logger.error(f"Failed to initiate shipment for order {order.id}: {e}")
                order.status = OrderStatus.SHIPPING_FAILED

        order = self.order_repository.update(order)
        return order