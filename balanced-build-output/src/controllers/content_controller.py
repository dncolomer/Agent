#!/usr/bin/env python3
"""
Content controller module.

This module handles incoming HTTP requests related to content management,
interacts with the content service, and returns appropriate responses.
"""

import logging

from flask import Blueprint, jsonify, request

from src.services.content_service import ContentService

# Set up a Blueprint for the content routes
content_bp = Blueprint('content', __name__, url_prefix='/content')

# Initialize the ContentService
content_service = ContentService()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@content_bp.route('/', methods=['GET'])
def get_all_content():
    """
    Retrieve all content items.

    Returns:
        A JSON response containing a list of all content items.
    """
    try:
        content_items = content_service.get_all_content()
        return jsonify(content_items)
    except Exception as e:
        logger.error(f"Error retrieving content: {e}")
        return jsonify({'error': str(e)}), 500


@content_bp.route('/<content_id>', methods=['GET'])
def get_content(content_id):
    """
    Retrieve a specific content item by ID.

    Args:
        content_id (str): The ID of the content item to retrieve.

    Returns:
        A JSON response containing the requested content item.
    """
    try:
        content_item = content_service.get_content(content_id)
        if content_item:
            return jsonify(content_item)
        else:
            return jsonify({'error': 'Content not found'}), 404
    except Exception as e:
        logger.error(f"Error retrieving content: {e}")
        return jsonify({'error': str(e)}), 500


@content_bp.route('/', methods=['POST'])
def create_content():
    """
    Create a new content item.

    Returns:
        A JSON response containing the newly created content item.
    """
    try:
        content_data = request.get_json()
        new_content = content_service.create_content(content_data)
        return jsonify(new_content), 201
    except Exception as e:
        logger.error(f"Error creating content: {e}")
        return jsonify({'error': str(e)}), 500


@content_bp.route('/<content_id>', methods=['PUT'])
def update_content(content_id):
    """
    Update an existing content item.

    Args:
        content_id (str): The ID of the content item to update.

    Returns:
        A JSON response containing the updated content item.
    """
    try:
        content_data = request.get_json()
        updated_content = content_service.update_content(content_id, content_data)
        if updated_content:
            return jsonify(updated_content)
        else:
            return jsonify({'error': 'Content not found'}), 404
    except Exception as e:
        logger.error(f"Error updating content: {e}")
        return jsonify({'error': str(e)}), 500


@content_bp.route('/<content_id>', methods=['DELETE'])
def delete_content(content_id):
    """
    Delete a content item.

    Args:
        content_id (str): The ID of the content item to delete.

    Returns:
        A JSON response indicating the success or failure of the operation.
    """
    try:
        success = content_service.delete_content(content_id)
        if success:
            return jsonify({'message': 'Content deleted successfully'})
        else:
            return jsonify({'error': 'Content not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting content: {e}")
        return jsonify({'error': str(e)}), 500