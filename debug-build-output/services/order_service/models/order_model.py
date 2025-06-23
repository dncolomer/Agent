#!/usr/bin/env python3
from dataclasses import dataclass, field
from typing import List
from uuid import UUID, uuid4
from enum import Enum
from decimal import Decimal

class OrderStatus(Enum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    SHIPPED = "Shipped"
    DELIVERED = "Delivered"
    CANCELLED = "Cancelled"

@dataclass
class Order:
    order_id: UUID = field(default_factory=uuid4)
    user_id: UUID
    product_ids: List[UUID]
    quantities: List[int]
    total_price: Decimal
    status: OrderStatus = OrderStatus.PENDING

    def __post_init__(self):
        if len(self.product_ids) != len(self.quantities):
            raise ValueError("Product IDs and quantities must have the same length.")
        if self.total_price < 0:
            raise ValueError("Total price cannot be negative.")

    def update_status(self, new_status: OrderStatus):
        if not isinstance(new_status, OrderStatus):
            raise ValueError("Invalid order status.")
        self.status = new_status

    def add_product(self, product_id: UUID, quantity: int, price: Decimal):
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")
        if price < 0:
            raise ValueError("Price cannot be negative.")
        self.product_ids.append(product_id)
        self.quantities.append(quantity)
        self.total_price += price * quantity

    def remove_product(self, product_id: UUID):
        if product_id not in self.product_ids:
            raise ValueError("Product not found in order.")
        index = self.product_ids.index(product_id)
        self.total_price -= self.quantities[index] * self.get_product_price(product_id)
        del self.product_ids[index]
        del self.quantities[index]

    def get_product_price(self, product_id: UUID) -> Decimal:
        # Placeholder for actual price retrieval logic
        return Decimal('0.00')  # This should be replaced with actual price retrieval logic

    def calculate_total_price(self):
        # Placeholder for actual total price calculation logic
        pass  # This should be replaced with actual total price calculation logic

    def __str__(self):
        return (f"Order ID: {self.order_id}\n"
                f"User ID: {self.user_id}\n"
                f"Products: {self.product_ids}\n"
                f"Quantities: {self.quantities}\n"
                f"Total Price: {self.total_price}\n"
                f"Status: {self.status.value}")