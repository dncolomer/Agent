#!/usr/bin/env python3
from flask import Flask, jsonify, request

app = Flask(__name__)

# In-memory database for simplicity
todos = []


@app.route('/todos', methods=['GET'])
def get_todos():
    """Endpoint to list all TODOs."""
    return jsonify(todos)


@app.route('/todos', methods=['POST'])
def create_todo():
    """Endpoint to create a new TODO."""
    data = request.get_json()
    if 'task' not in data:
        return jsonify({'error': 'Task is required'}), 400
    
    todo = {
        'id': len(todos) + 1,
        'task': data['task'],
        'status': 'pending'
    }
    todos.append(todo)
    return jsonify(todo), 201


@app.route('/todos/<int:todo_id>', methods=['PUT'])
def update_todo(todo_id):
    """Endpoint to update an existing TODO."""
    data = request.get_json()
    todo = next((item for item in todos if item['id'] == todo_id), None)
    if todo is None:
        return jsonify({'error': 'TODO not found'}), 404
    if 'task' in data:
        todo['task'] = data['task']
    if 'status' in data:
        todo['status'] = data['status']
    return jsonify(todo)


@app.route('/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    """Endpoint to delete an existing TODO."""
    global todos
    todo = next((item for item in todos if item['id'] == todo_id), None)
    if todo is None:
        return jsonify({'error': 'TODO not found'}), 404
    todos = [item for item in todos if item['id'] != todo_id]
    return jsonify({'success': True}), 204


if __name__ == '__main__':
    app.run(debug=True)