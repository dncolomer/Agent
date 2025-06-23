#!/usr/bin/env python3
# orders_service.py

class OrdersService:
    def __init__(self):
        self.orders = []

    def create_order(self, order_id, customer_id, total_amount):
        """
        Create a new order with the provided order_id, customer_id, and total_amount.
        """
        order = {
            'order_id': order_id,
            'customer_id': customer_id,
            'total_amount': total_amount
        }
        self.orders.append(order)
        return order

    def get_order_by_id(self, order_id):
        """
        Retrieve an order by its order_id.
        Returns the order if found, else returns None.
        """
        for order in self.orders:
            if order['order_id'] == order_id:
                return order
        return None

    def get_orders_by_customer(self, customer_id):
        """
        Retrieve all orders for a specific customer_id.
        Returns a list of orders for the customer.
        """
        customer_orders = [order for order in self.orders if order['customer_id'] == customer_id]
        return customer_orders

    def update_order_total_amount(self, order_id, new_total_amount):
        """
        Update the total amount for a specific order identified by order_id.
        Returns True if the update is successful, else False.
        """
        for order in self.orders:
            if order['order_id'] == order_id:
                order['total_amount'] = new_total_amount
                return True
        return False

    def delete_order(self, order_id):
        """
        Delete an order based on its order_id.
        Returns True if the order is successfully deleted, else False.
        """
        for order in self.orders:
            if order['order_id'] == order_id:
                self.orders.remove(order)
                return True
        return False

# Sample Usage:
# orders_service = OrdersService()
# orders_service.create_order(1, 101, 50.0)
# orders_service.create_order(2, 102, 75.0)
# print(orders_service.get_orders_by_customer(101))