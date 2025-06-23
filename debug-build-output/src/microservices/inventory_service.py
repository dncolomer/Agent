#!/usr/bin/env python3
from flask import Flask, jsonify, request

app = Flask(__name__)

inventory = [
    {"id": 1, "item": "Keyboard", "quantity": 50},
    {"id": 2, "item": "Mouse", "quantity": 100},
    {"id": 3, "item": "Monitor", "quantity": 20}
]

# Endpoint to get all items in the inventory
@app.route('/inventory', methods=['GET'])
def get_inventory():
    return jsonify(inventory)

# Endpoint to add a new item to the inventory
@app.route('/inventory', methods=['POST'])
def add_item():
    data = request.get_json()
    if 'item' not in data or 'quantity' not in data:
        return jsonify({"error": "Missing data"}), 400
    new_item = {
        "id": len(inventory) + 1,
        "item": data['item'],
        "quantity": data['quantity']
    }
    inventory.append(new_item)
    return jsonify({"message": "Item added successfully"})

# Endpoint to update the quantity of a specific item in the inventory
@app.route('/inventory/<int:item_id>', methods=['PUT'])
def update_quantity(item_id):
    data = request.get_json()
    for item in inventory:
        if item['id'] == item_id:
            item['quantity'] = data['quantity']
            return jsonify({"message": "Quantity updated successfully"})
    return jsonify({"error": "Item not found"}), 404

if __name__ == '__main__':
    app.run()