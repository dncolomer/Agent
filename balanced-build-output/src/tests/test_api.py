#!/usr/bin/env python3
import pytest
import requests

BASE_URL = "http://localhost:5000/api"

@pytest.fixture
def api_client():
    """Fixture to provide a test client for API requests."""
    return requests.Session()

def test_get_content(api_client):
    """Test the GET endpoint for retrieving content."""
    response = api_client.get(f"{BASE_URL}/content")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_post_content(api_client):
    """Test the POST endpoint for creating new content."""
    new_content = {
        "title": "Test Title",
        "body": "This is a test body."
    }
    response = api_client.post(f"{BASE_URL}/content", json=new_content)
    assert response.status_code == 201
    assert response.json().get("title") == new_content["title"]

def test_get_content_by_id(api_client):
    """Test the GET endpoint for retrieving content by ID."""
    content_id = 1  # Assuming this ID exists in the test database
    response = api_client.get(f"{BASE_URL}/content/{content_id}")
    assert response.status_code == 200
    assert response.json().get("id") == content_id

def test_update_content(api_client):
    """Test the PUT endpoint for updating existing content."""
    content_id = 1  # Assuming this ID exists in the test database
    updated_content = {
        "title": "Updated Title",
        "body": "This is an updated body."
    }
    response = api_client.put(f"{BASE_URL}/content/{content_id}", json=updated_content)
    assert response.status_code == 200
    assert response.json().get("title") == updated_content["title"]

def test_delete_content(api_client):
    """Test the DELETE endpoint for removing content."""
    content_id = 1  # Assuming this ID exists in the test database
    response = api_client.delete(f"{BASE_URL}/content/{content_id}")
    assert response.status_code == 204

def test_get_nonexistent_content(api_client):
    """Test the GET endpoint for a nonexistent content ID."""
    nonexistent_id = 9999
    response = api_client.get(f"{BASE_URL}/content/{nonexistent_id}")
    assert response.status_code == 404

def test_post_invalid_content(api_client):
    """Test the POST endpoint with invalid content data."""
    invalid_content = {
        "title": "",  # Title is required
        "body": "This is a test body."
    }
    response = api_client.post(f"{BASE_URL}/content", json=invalid_content)
    assert response.status_code == 400

def test_update_nonexistent_content(api_client):
    """Test the PUT endpoint for updating a nonexistent content ID."""
    nonexistent_id = 9999
    updated_content = {
        "title": "Updated Title",
        "body": "This is an updated body."
    }
    response = api_client.put(f"{BASE_URL}/content/{nonexistent_id}", json=updated_content)
    assert response.status_code == 404

def test_delete_nonexistent_content(api_client):
    """Test the DELETE endpoint for a nonexistent content ID."""
    nonexistent_id = 9999
    response = api_client.delete(f"{BASE_URL}/content/{nonexistent_id}")
    assert response.status_code == 404