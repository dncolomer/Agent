#!/usr/bin/env python3
from flask import Blueprint, request, jsonify, abort
from src.models import Content, db

# Define the Blueprint for the API routes
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# Helper function to get content by ID
def get_content_or_404(content_id):
    content = Content.query.get(content_id)
    if content is None:
        abort(404, description=f"Content with ID {content_id} not found")
    return content

# Route for creating new content
@api_v1.route('/content', methods=['POST'])
def create_content():
    data = request.get_json()
    if not data or 'title' not in data or 'body' not in data:
        abort(400, description="Invalid input: 'title' and 'body' are required fields")
    
    new_content = Content(title=data['title'], body=data['body'])
    db.session.add(new_content)
    db.session.commit()
    return jsonify(new_content.to_dict()), 201

# Route for retrieving all content
@api_v1.route('/content', methods=['GET'])
def get_all_content():
    contents = Content.query.all()
    return jsonify([content.to_dict() for content in contents]), 200

# Route for retrieving a single content item by ID
@api_v1.route('/content/<int:content_id>', methods=['GET'])
def get_content(content_id):
    content = get_content_or_404(content_id)
    return jsonify(content.to_dict()), 200

# Route for updating content by ID
@api_v1.route('/content/<int:content_id>', methods=['PUT'])
def update_content(content_id):
    content = get_content_or_404(content_id)
    data = request.get_json()
    if not data:
        abort(400, description="Invalid input: No data provided")
    
    content.title = data.get('title', content.title)
    content.body = data.get('body', content.body)
    db.session.commit()
    return jsonify(content.to_dict()), 200

# Route for deleting content by ID
@api_v1.route('/content/<int:content_id>', methods=['DELETE'])
def delete_content(content_id):
    content = get_content_or_404(content_id)
    db.session.delete(content)
    db.session.commit()
    return jsonify({"message": f"Content with ID {content_id} deleted"}), 200