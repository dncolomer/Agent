#!/usr/bin/env python3
from flask import Flask, jsonify, request

# Initialize Flask application
app = Flask(__name__)

# In-memory database simulation
todos = [
    {'id': 1, 'task': 'Buy milk', 'completed': False},
    {'id': 2, 'task': 'Learn Flask', 'completed': False},
    {'id': 3, 'task': 'Read a book', 'completed': False}
]

# Route to get all TODOs
@app.route('/todos', methods=['GET'])
def get_todos():
    """Get all todos."""
    return jsonify(todos), 200

# Route to add a new TODO
@app.route('/todos', methods=['POST'])
def add_todo():
    """Add a new todo."""
    try:
        new_todo = request.get_json()
        new_todo['id'] = len(todos) + 1
        todos.append(new_todo)
        return jsonify(new_todo), 201
    except Exception as e:
        return jsonify({"error": "Error adding todo"}), 400

# Route to update a TODO by id
@app.route('/todos/<int:todo_id>', methods=['PUT'])
def update_todo(todo_id):
    """Update an existing todo."""
    try:
        todo_update = request.get_json()
        todo = next((todo for todo in todos if todo['id'] == todo_id), None)
        if todo is None:
            return jsonify({"error": "Todo not found"}), 404
        todo.update(todo_update)
        return jsonify(todo), 200
    except Exception as e:
        return jsonify({"error": "Error updating todo"}), 400

# Route to delete a TODO by id
@app.route('/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    """Delete an existing todo."""
    try:
        todo = next((todo for todo in todos if todo['id'] == todo_id), None)
        if todo is None:
            return jsonify({"error": "Todo not found"}), 404
        todos.remove(todo)
        return jsonify({"message": "Todo deleted"}), 200
    except Exception as e:
        return jsonify({"error": "Error deleting todo"}), 400

if __name__ == '__main__':
    # Run the Flask application
    app.run(debug=True)