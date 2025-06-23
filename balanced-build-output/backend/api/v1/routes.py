#!/usr/bin/env python3
from fastapi import APIRouter, HTTPException, status
from typing import List
from pydantic import BaseModel

# Define the router for version 1 of the API
router = APIRouter()

# Pydantic models for request and response bodies
class ContentCreate(BaseModel):
    title: str
    body: str
    author_id: int

class ContentUpdate(BaseModel):
    title: str = None
    body: str = None

class ContentResponse(BaseModel):
    id: int
    title: str
    body: str
    author_id: int

# In-memory storage for demonstration purposes
content_db = []
content_id_counter = 1

@router.post("/content/", response_model=ContentResponse, status_code=status.HTTP_201_CREATED)
async def create_content(content: ContentCreate):
    """
    Create a new content item.
    """
    global content_id_counter
    new_content = {
        "id": content_id_counter,
        "title": content.title,
        "body": content.body,
        "author_id": content.author_id
    }
    content_db.append(new_content)
    content_id_counter += 1
    return new_content

@router.get("/content/", response_model=List[ContentResponse])
async def get_all_content():
    """
    Retrieve all content items.
    """
    return content_db

@router.get("/content/{content_id}", response_model=ContentResponse)
async def get_content(content_id: int):
    """
    Retrieve a content item by its ID.
    """
    content_item = next((item for item in content_db if item["id"] == content_id), None)
    if content_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    return content_item

@router.put("/content/{content_id}", response_model=ContentResponse)
async def update_content(content_id: int, content: ContentUpdate):
    """
    Update a content item by its ID.
    """
    content_item = next((item for item in content_db if item["id"] == content_id), None)
    if content_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    
    if content.title is not None:
        content_item["title"] = content.title
    if content.body is not None:
        content_item["body"] = content.body
    
    return content_item

@router.delete("/content/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content(content_id: int):
    """
    Delete a content item by its ID.
    """
    global content_db
    content_db = [item for item in content_db if item["id"] != content_id]
    return None