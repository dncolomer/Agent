#!/usr/bin/env python3
"""
Content Service Module

This module provides the core business logic and services for managing content
in the content management system.
"""

from typing import List, Optional
from datetime import datetime
from src.models.content import Content
from src.repositories.content_repository import ContentRepository

# Instantiate the ContentRepository
content_repository = ContentRepository()

def create_content(title: str, body: str, author: str, category: str) -> Content:
    """
    Create a new content item.

    Args:
        title (str): The title of the content.
        body (str): The body of the content.
        author (str): The author of the content.
        category (str): The category of the content.

    Returns:
        Content: The newly created content item.
    """
    content = Content(title=title, body=body, author=author, category=category)
    content_repository.create(content)
    return content

def get_content_by_id(content_id: int) -> Optional[Content]:
    """
    Get a content item by its ID.

    Args:
        content_id (int): The ID of the content item.

    Returns:
        Optional[Content]: The content item if found, otherwise None.
    """
    return content_repository.get_by_id(content_id)

def get_all_content() -> List[Content]:
    """
    Get all content items.

    Returns:
        List[Content]: A list of all content items.
    """
    return content_repository.get_all()

def update_content(content_id: int, title: Optional[str] = None, body: Optional[str] = None,
                   author: Optional[str] = None, category: Optional[str] = None) -> Optional[Content]:
    """
    Update an existing content item.

    Args:
        content_id (int): The ID of the content item to update.
        title (Optional[str]): The new title of the content item (if provided).
        body (Optional[str]): The new body of the content item (if provided).
        author (Optional[str]): The new author of the content item (if provided).
        category (Optional[str]): The new category of the content item (if provided).

    Returns:
        Optional[Content]: The updated content item if found, otherwise None.
    """
    content = content_repository.get_by_id(content_id)
    if content:
        if title:
            content.title = title
        if body:
            content.body = body
        if author:
            content.author = author
        if category:
            content.category = category
        content.updated_at = datetime.utcnow()
        content_repository.update(content)
        return content
    return None

def delete_content(content_id: int) -> bool:
    """
    Delete a content item by its ID.

    Args:
        content_id (int): The ID of the content item to delete.

    Returns:
        bool: True if the content item was deleted successfully, False otherwise.
    """
    content = content_repository.get_by_id(content_id)
    if content:
        content_repository.delete(content)
        return True
    return False