import json

import requests

# Base URL for the API
BASE_URL = "http://localhost:8000/api/v1"

def test_list_datasets():
    """Test listing all datasets."""
    print("Testing list datasets...")
    response = requests.get(f"{BASE_URL}/datasets/")
    print(f"Status Code: {response.status_code}")
    print("Response:", json.dumps(response.json(), indent=2))
    print("-" * 50)

def test_create_dataset():
    """Test creating a new dataset."""
    print("Testing create dataset...")
    data = {
        "name": "Test Dataset",
        "description": "A test dataset",
        "is_public": False
    }
    response = requests.post(f"{BASE_URL}/datasets/", json=data)
    print(f"Status Code: {response.status_code}")
    print("Response:", json.dumps(response.json(), indent=2))
    print("-" * 50)
    return response.json().get("id")

def test_get_dataset(dataset_id: str):
    """Test getting a specific dataset."""
    print(f"Testing get dataset {dataset_id}...")
    response = requests.get(f"{BASE_URL}/datasets/{dataset_id}")
    print(f"Status Code: {response.status_code}")
    print("Response:", json.dumps(response.json(), indent=2))
    print("-" * 50)

def test_import_yolo_dataset():
    """Test importing a YOLO dataset."""
    print("Testing YOLO dataset import...")
    
    # You'll need to provide a path to a test YOLO dataset ZIP file
    test_zip_path = "path/to/your/test_dataset.zip"
    
    with open(test_zip_path, "rb") as f:
        files = {"file": ("test_dataset.zip", f, "application/zip")}
        data = {"dataset_name": "Test YOLO Import"}
        response = requests.post(
            f"{BASE_URL}/datasets/import/yolo",
            files=files,
            data=data
        )
    
    print(f"Status Code: {response.status_code}")
    try:
        print("Response:", json.dumps(response.json(), indent=2))
    except:
        print("Response:", response.text)
    print("-" * 50)

if __name__ == "__main__":
    # Run tests
    test_list_datasets()
    dataset_id = test_create_dataset()
    if dataset_id:
        test_get_dataset(dataset_id)
    
    # Uncomment to test YOLO import (requires a test dataset)
    # test_import_yolo_dataset()
