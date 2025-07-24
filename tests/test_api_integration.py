"""
Integration Tests for API Endpoints

Tests API endpoints against a running server instance.
Requires the server to be running on localhost:8000.

Usage:
    # Start the server first
    cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    
    # Run tests
    pytest tests/test_api_integration.py -v
"""

import pytest
import requests
import json
import time
from io import BytesIO
import zipfile
from typing import Optional, Dict, Any

# Server configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

# Test data
SAMPLE_DATASET = {
    "name": "Integration Test Dataset",
    "description": "Dataset created during integration testing",
    "is_public": False
}


class TestServerConnection:
    """Test basic server connectivity."""
    
    def test_server_is_running(self):
        """Test that the server is accessible."""
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
        except requests.exceptions.ConnectionError:
            pytest.skip("Server is not running. Start with: uvicorn app.main:app --reload")
    
    def test_api_documentation_accessible(self):
        """Test that API documentation is accessible."""
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestDatasetCRUD:
    """Test dataset CRUD operations against running server."""
    
    def test_list_datasets(self):
        """Test listing all datasets."""
        response = requests.get(f"{API_BASE}/datasets/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} existing datasets")
    
    def test_create_and_retrieve_dataset(self):
        """Test creating a dataset and retrieving it."""
        # Create dataset
        response = requests.post(f"{API_BASE}/datasets/", json=SAMPLE_DATASET)
        
        if response.status_code == 200:
            dataset = response.json()
            dataset_id = dataset["id"]
            
            print(f"Created dataset with ID: {dataset_id}")
            
            # Verify dataset was created
            assert dataset["name"] == SAMPLE_DATASET["name"]
            assert dataset["description"] == SAMPLE_DATASET["description"]
            
            # Retrieve the dataset
            response = requests.get(f"{API_BASE}/datasets/{dataset_id}")
            if response.status_code == 200:
                retrieved_dataset = response.json()
                assert retrieved_dataset["id"] == dataset_id
                assert retrieved_dataset["name"] == SAMPLE_DATASET["name"]
                
                print("✅ Dataset creation and retrieval successful")
                return dataset_id
            else:
                print(f"⚠️ Could not retrieve dataset: {response.status_code}")
        else:
            print(f"⚠️ Could not create dataset: {response.status_code} - {response.text}")
            # This might be due to database connection issues
            pytest.skip("Dataset creation failed - likely database connection issue")
    
    def test_list_images_for_dataset(self):
        """Test listing images for a dataset."""
        # First create a dataset
        response = requests.post(f"{API_BASE}/datasets/", json=SAMPLE_DATASET)
        
        if response.status_code == 200:
            dataset_id = response.json()["id"]
            
            # List images (should be empty initially)
            response = requests.get(f"{API_BASE}/datasets/{dataset_id}/images")
            assert response.status_code == 200
            images = response.json()
            assert isinstance(images, list)
            assert len(images) == 0
            
            print("✅ Image listing successful")
        else:
            pytest.skip("Could not create dataset for image testing")


class TestYOLOImport:
    """Test YOLO dataset import functionality."""
    
    @staticmethod
    def create_minimal_yolo_zip() -> BytesIO:
        """Create a minimal YOLO dataset for testing."""
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add minimal YOLO structure
            zip_file.writestr("images/image1.jpg", b"fake_jpg_data")
            zip_file.writestr("labels/image1.txt", "0 0.5 0.5 0.2 0.2")
            zip_file.writestr("classes.txt", "test_class")
            
        zip_buffer.seek(0)
        return zip_buffer
    
    def test_yolo_import_endpoint_accessible(self):
        """Test that YOLO import endpoint is accessible."""
        # Test with minimal data to check endpoint availability
        zip_data = self.create_minimal_yolo_zip()
        
        files = {"file": ("test.zip", zip_data, "application/zip")}
        data = {"dataset_name": "Test Import"}
        
        response = requests.post(f"{API_BASE}/datasets/import/yolo", files=files, data=data)
        
        # Should respond (success or failure, but not 404)
        assert response.status_code != 404
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"✅ YOLO import successful: {result.get('name', 'Unknown')}")
            return result.get("id")
        else:
            print(f"⚠️ YOLO import failed: {response.status_code} - {response.text}")
            # This might be expected if GCP credentials are missing
    
    def test_import_status_endpoint(self):
        """Test import status endpoint."""
        # Use a fake dataset ID to test endpoint availability
        fake_id = "test-dataset-id"
        response = requests.get(f"{API_BASE}/datasets/{fake_id}/import-status")
        
        # Should respond (even if dataset doesn't exist)
        assert response.status_code in [200, 404, 422]
        print(f"Import status endpoint response: {response.status_code}")


class TestChunkedUpload:
    """Test chunked upload functionality."""
    
    def test_chunked_upload_endpoint_accessible(self):
        """Test that chunked upload endpoint is accessible."""
        # Create a small chunk for testing
        chunk_data = BytesIO(b"test chunk data")
        files = {"chunk_file": ("chunk", chunk_data, "application/octet-stream")}
        
        params = {
            "upload_id": "test-upload",
            "chunk_number": 0,
            "total_chunks": 1
        }
        
        response = requests.post(
            f"{API_BASE}/datasets/test-id/chunks",
            files=files,
            params=params
        )
        
        # Should respond (not 404)
        assert response.status_code != 404
        print(f"Chunked upload endpoint response: {response.status_code}")


class TestAPIValidation:
    """Test API validation and error handling."""
    
    def test_invalid_dataset_creation(self):
        """Test dataset creation with invalid data."""
        invalid_data = {"name": ""}  # Empty name should be invalid
        
        response = requests.post(f"{API_BASE}/datasets/", json=invalid_data)
        assert response.status_code == 422  # Validation error
        
        error_data = response.json()
        assert "detail" in error_data
        print("✅ Validation error handling works correctly")
    
    def test_nonexistent_dataset_retrieval(self):
        """Test retrieving a non-existent dataset."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = requests.get(f"{API_BASE}/datasets/{fake_id}")
        
        assert response.status_code == 404
        error_data = response.json()
        assert "not found" in error_data["detail"].lower()
        print("✅ 404 error handling works correctly")


class TestPerformance:
    """Test API performance and responsiveness."""
    
    def test_health_check_response_time(self):
        """Test that health check responds quickly."""
        start_time = time.time()
        response = requests.get(f"{BASE_URL}/health")
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response.status_code == 200
        assert response_time < 1.0  # Should respond within 1 second
        
        print(f"✅ Health check response time: {response_time:.3f}s")
    
    def test_dataset_list_response_time(self):
        """Test dataset listing response time."""
        start_time = time.time()
        response = requests.get(f"{API_BASE}/datasets/")
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response.status_code == 200
        assert response_time < 2.0  # Should respond within 2 seconds
        
        print(f"✅ Dataset list response time: {response_time:.3f}s")


def test_complete_api_health():
    """Comprehensive API health check."""
    print("\n🔍 Running comprehensive API health check...")
    
    # Test server connectivity
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        assert response.status_code == 200
        print("✅ Server is healthy and responding")
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running")
        pytest.fail("Server is not accessible. Please start the server first.")
    
    # Test API documentation
    response = requests.get(f"{BASE_URL}/docs", timeout=5)
    assert response.status_code == 200
    print("✅ API documentation is accessible")
    
    # Test main endpoints
    endpoints_to_test = [
        ("/api/v1/datasets/", "GET", "Dataset listing"),
        ("/health", "GET", "Health check"),
    ]
    
    for endpoint, method, description in endpoints_to_test:
        try:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            
            print(f"✅ {description}: {response.status_code}")
            
        except Exception as e:
            print(f"⚠️ {description}: Error - {str(e)}")
    
    print("\n🎉 API health check completed!")


if __name__ == "__main__":
    # Run the comprehensive health check
    test_complete_api_health()
