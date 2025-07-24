import pytest
import sys
import os
from fastapi.testclient import TestClient

# Add the backend directory to the Python path
backend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
sys.path.insert(0, backend_path)

from app.main import app

client = TestClient(app)

def test_read_root():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "status" in data
    assert data["status"] == "healthy"
    assert data["service"] == "YOLO Dataset Annotation Service"

def test_list_datasets():
    """Test listing datasets."""
    response = client.get("/api/v1/datasets/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_create_dataset():
    """Test creating a new dataset."""
    dataset_data = {
        "name": "Test Dataset",
        "description": "A test dataset",
        "format": "yolo"
    }
    response = client.post("/api/v1/datasets/", json=dataset_data)
    assert response.status_code == 200
    data = response.json()
    assert "name" in data, f"'name' key not in response: {data}"
    assert data["name"] == dataset_data["name"]
    assert data["description"] == dataset_data["description"]
    assert data["format"] == dataset_data["format"]
    assert "id" in data
    assert "image_count" in data
    assert data["image_count"] == 0
    
    # Clean up - delete the test dataset
    if "id" in data:
        # Note: Implement delete endpoint if needed
        pass

