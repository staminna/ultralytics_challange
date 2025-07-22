import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

def test_read_root():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "YOLO Dataset Annotation Service is running"}

def test_list_datasets():
    """Test listing datasets."""
    response = client.get("/api/v1/datasets/")
    assert response.status_code == 200
    assert isinstance(response.json()["datasets"], list)
    assert "total" in response.json()

@pytest.mark.asyncio
async def test_create_dataset():
    """Test creating a new dataset."""
    dataset_data = {
        "name": "Test Dataset",
        "description": "A test dataset",
        "is_public": False
    }
    response = client.post("/api/v1/datasets/", json=dataset_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == dataset_data["name"]
    assert data["description"] == dataset_data["description"]
    assert data["is_public"] == dataset_data["is_public"]
    
    # Clean up - delete the test dataset
    if "id" in data:
        # Note: Implement delete endpoint if needed
        pass
