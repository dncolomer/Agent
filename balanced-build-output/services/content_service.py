#!/usr/bin/env python3
"""
Content Service Module

This module contains the core business logic for managing content, including CRUD operations, validation, and data processing.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

from models import Content, User
from database import db_session
from exceptions import ContentValidationError, ContentNotFoundError

logger = logging.getLogger(__name__)

def create_content(user_id: int, title: str, body: str, tags: Optional[List[str]] = None) -> Content:
    """
    Create a new content item.

    Args:
        user_id (int): The ID of the user creating the content.
        title (str): The title of the content.
        body (str): The body or content of the content item.
        tags (Optional[List[str]]): A list of tags associated with the content.

    Returns:
        Content: The newly created content item.

    Raises:
        ContentValidationError: If the provided data is invalid or incomplete.
    """
    # Validate input data
    if not title or not body:
        raise ContentValidationError("Title and body are required.")

    # Create the content object
    content = Content(
        user_id=user_id,
        title=title,
        body=body,
        tags=tags or [],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    # Save the content to the database
    db_session.add(content)
    db_session.commit()

    logger.info(f"New content created: {content.id}")
    return content

def get_content(content_id: int) -> Content:
    """
    Retrieve a content item by its ID.

    Args:
        content_id (int): The ID of the content item to retrieve.

    Returns:
        Content: The requested content item.

    Raises:
        ContentNotFoundError: If the content item with the given ID is not found.
    """
    content = db_session.query(Content).get(content_id)
    if not content:
        raise ContentNotFoundError(f"Content with ID {content_id} not found.")

    return content

def update_content(content_id: int, title: Optional[str] = None, body: Optional[str] = None, tags: Optional[List[str]] = None) -> Content:
    """
    Update an existing content item.

    Args:
        content_id (int): The ID of the content item to update.
        title (Optional[str]): The new title for the content item.
        body (Optional[str]): The new body or content for the content item.
        tags (Optional[List[str]]): The new list of tags for the content item.

    Returns:
        Content: The updated content item.

    Raises:
        ContentNotFoundError: If the content item with the given ID is not found.
        ContentValidationError: If the provided data is invalid or incomplete.
    """
    content = db_session.query(Content).get(content_id)
    if not content:
        raise ContentNotFoundError(f"Content with ID {content_id} not found.")

    # Validate input data
    if not title and not body and not tags:
        raise ContentValidationError("At least one field must be provided for update.")

    # Update the content object
    if title:
        content.title = title
    if body:
        content.body = body
    if tags:
        content.tags = tags

    content.updated_at = datetime.utcnow()

    # Save the updated content to the database
    db_session.commit()

    logger.info(f"Content with ID {content_id} updated.")
    return content

def delete_content(content_id: int) -> None:
    """
    Delete a content item.

    Args:
        content_id (int): The ID of the content item to delete.

    Raises:
        ContentNotFoundError: If the content item with the given ID is not found.
    """
    content = db_session.query(Content).get(content_id)
    if not content:
        raise ContentNotFoundError(f"Content with ID {content_id} not found.")

    # Delete the content from the database
    db_session.delete(content)
    db_session.commit()

    logger.info(f"Content with ID {content_id} deleted.")

def get_user_content(user_id: int) -> List[Content]:
    """
    Retrieve all content items created by a user.

    Args:
        user_id (int): The ID of the user.

    Returns:
        List[Content]: A list of content items created by the user.
    """
    user_content = db_session.query(Content).filter_by(user_id=user_id).all()
    return user_content

def search_content(query: str, tags: Optional[List[str]] = None) -> List[Content]:
    """
    Search for content items based on a query and optional tags.

    Args:
        query (str): The search query string.
        tags (Optional[List[str]]): A list of tags to filter the search.

    Returns:
        List[Content]: A list of content items matching the search criteria.
    """
    # Build the search query
    search_query = db_session.query(Content).filter(Content.title.ilike(f"%{query}%") | Content.body.ilike(f"%{query}%"))

    if tags:
        search_query = search_query.filter(Content.tags.any(tag.lower() in [t.lower() for t in tags]))

    results = search_query.all()
    return results