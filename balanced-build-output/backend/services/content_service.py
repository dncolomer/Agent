#!/usr/bin/env python3
"""
Content Service Module

This module contains core business logic for managing content,
including CRUD operations and content validation.
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, validator

# Content Data Models
class Content(BaseModel):
    """
    Represents a content item.
    """
    id: Optional[int] = None
    title: str
    body: str
    author: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @validator('title')
    def title_must_not_be_blank(cls, value):
        """
        Validates that the title is not blank.
        """
        if not value.strip():
            raise ValueError('Title cannot be blank')
        return value

    @validator('body')
    def body_must_not_be_blank(cls, value):
        """
        Validates that the body is not blank.
        """
        if not value.strip():
            raise ValueError('Body cannot be blank')
        return value

    @validator('author')
    def author_must_not_be_blank(cls, value):
        """
        Validates that the author is not blank.
        """
        if not value.strip():
            raise ValueError('Author cannot be blank')
        return value

# In-memory data store
_content_store = []

def create_content(content: Content) -> Content:
    """
    Creates a new content item.
    """
    content.created_at = datetime.now()
    content.updated_at = datetime.now()
    _content_store.append(content)
    return content

def get_content(content_id: int) -> Optional[Content]:
    """
    Retrieves a content item by ID.
    """
    for content in _content_store:
        if content.id == content_id:
            return content
    return None

def get_all_content() -> List[Content]:
    """
    Retrieves all content items.
    """
    return _content_store

def update_content(content_id: int, updated_content: Content) -> Optional[Content]:
    """
    Updates an existing content item.
    """
    for i, content in enumerate(_content_store):
        if content.id == content_id:
            updated_content.id = content_id
            updated_content.created_at = content.created_at
            updated_content.updated_at = datetime.now()
            _content_store[i] = updated_content
            return updated_content
    return None

def delete_content(content_id: int) -> bool:
    """
    Deletes a content item by ID.
    """
    for i, content in enumerate(_content_store):
        if content.id == content_id:
            del _content_store[i]
            return True
    return False