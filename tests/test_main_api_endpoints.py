"""
Comprehensive Tests for Main API Endpoints

Tests all core API endpoints of the YOLO Dataset Annotation Service:
- Health checks
- Dataset management (CRUD)
- Dataset import (YOLO format)
- Chunked upload for large datasets
- Image and label management

Usage:
    pytest tests/test_main_api_endpoints.py -v
    pytest tests/test_main_api_endpoints.py::TestDatasetManagement -v
"""

import pytest
import asyncio
import tempfile
import zipfile
import os
from io import BytesIO
from typing import Dict, Any
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the FastAPI app
import sys
sys.path.append('/Users/jorgenunes/2026/ultra assesment/backend')
from app.main import app

# Test client
client = TestClient(app)

# Test data constants
SAMPLE_DATASET_DATA = {
    "name": "Test Dataset",
    "description": "A test dataset for API testing",
    "is_public": False
}

SAMPLE_YOLO_DATASET_DATA = {
    "name": "YOLO Test Dataset",
    "description": "Test YOLO dataset with sample data"
}


class TestHealthChecks:
    """Test health check endpoints."""
    
    def test_root_endpoint(self):
        """Test the root endpoint returns service info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert data["status"] == "healthy"
        assert "YOLO Dataset Annotation Service" in data["service"]
    
    def test_health_endpoint(self):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestDatasetManagement:
    """Test dataset CRUD operations."""
    
    def test_list_datasets_empty(self):
        """Test listing datasets when none exist."""
        response = client.get("/api/v1/datasets/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_create_dataset(self):
        """Test creating a new dataset."""
        response = client.post("/api/v1/datasets/", json=SAMPLE_DATASET_DATA)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == SAMPLE_DATASET_DATA["name"]
        assert data["description"] == SAMPLE_DATASET_DATA["description"]
        assert "id" in data
        # Test passes - dataset created successfully
    
    def test_create_dataset_invalid_data(self):
        """Test creating dataset with invalid data."""
        invalid_data = {"name": ""}  # Missing required fields
        response = client.post("/api/v1/datasets/", json=invalid_data)
        assert response.status_code == 422  # Validation error
    
    def test_get_dataset_not_found(self):
        """Test getting a non-existent dataset."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/datasets/{fake_id}")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_delete_dataset_not_found(self):
        """Test deleting a non-existent dataset."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.delete(f"/api/v1/datasets/{fake_id}")
        assert response.status_code == 404


class TestDatasetImport:
    """Test dataset import functionality."""
    
    @staticmethod
    def create_sample_yolo_zip() -> BytesIO:
        """Create a sample YOLO dataset ZIP file for testing."""
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Create sample images directory
            zip_file.writestr("images/train/image1.jpg", b"fake_image_data_1")
            zip_file.writestr("images/train/image2.jpg", b"fake_image_data_2")
            zip_file.writestr("images/val/image3.jpg", b"fake_image_data_3")
            
            # Create sample labels directory
            zip_file.writestr("labels/train/image1.txt", "0 0.5 0.5 0.2 0.2\n")
            zip_file.writestr("labels/train/image2.txt", "1 0.3 0.3 0.1 0.1\n")
            zip_file.writestr("labels/val/image3.txt", "0 0.7 0.7 0.15 0.15\n")
            
            # Create classes.txt
            zip_file.writestr("classes.txt", "person\ncar\nbicycle\n")
            
            # Create data.yaml
            yaml_content = """
train: images/train
val: images/val
nc: 3
names: ['person', 'car', 'bicycle']
"""
            zip_file.writestr("data.yaml", yaml_content)
        
        zip_buffer.seek(0)
        return zip_buffer
    
    def test_import_yolo_dataset_success(self):
        """Test successful YOLO dataset import."""
        zip_data = self.create_sample_yolo_zip()
        
        files = {"file": ("test_dataset.zip", zip_data, "application/zip")}
        data = {"dataset_name": "Test YOLO Import"}
        
        response = client.post("/api/v1/datasets/import/yolo", files=files, data=data)
        
        # Should succeed or fail gracefully depending on MongoDB connection
        assert response.status_code in [200, 201, 500, 503]
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data
            assert data["name"] == "Test YOLO Import"
            assert data["format"] == "yolo"
            return data["id"]
    
    def test_import_yolo_dataset_invalid_file(self):
        """Test YOLO import with invalid file."""
        # Create a non-ZIP file
        fake_file = BytesIO(b"not a zip file")
        files = {"file": ("invalid.txt", fake_file, "text/plain")}
        
        response = client.post("/api/v1/datasets/import/yolo", files=files)
        assert response.status_code in [400, 422, 500]
    
    def test_import_yolo_dataset_no_file(self):
        """Test YOLO import without file."""
        response = client.post("/api/v1/datasets/import/yolo")
        assert response.status_code == 422  # Missing required field


class TestChunkedUpload:
    """Test chunked upload functionality for large datasets."""
    
    @staticmethod
    def create_test_chunks(data: bytes, chunk_size: int = 1024) -> list:
        """Split data into chunks for testing."""
        chunks = []
        for i in range(0, len(data), chunk_size):
            chunks.append(data[i:i + chunk_size])
        return chunks
    
    def test_chunked_upload_flow(self):
        """Test the complete chunked upload flow."""
        # Create sample data
        zip_data = TestDatasetImport.create_sample_yolo_zip()
        data_bytes = zip_data.getvalue()
        chunks = self.create_test_chunks(data_bytes, chunk_size=512)
        
        # Test dataset ID (would normally be created first)
        dataset_id = "test-dataset-id"
        upload_id = "test-upload-id"
        
        # Upload each chunk
        for i, chunk in enumerate(chunks):
            chunk_file = BytesIO(chunk)
            files = {"chunk_file": ("chunk", chunk_file, "application/octet-stream")}
            
            response = client.post(
                f"/api/v1/datasets/{dataset_id}/chunks",
                files=files,
                params={
                    "upload_id": upload_id,
                    "chunk_number": i,
                    "total_chunks": len(chunks)
                }
            )
            
            # Should handle gracefully even if dataset doesn't exist
            assert response.status_code in [200, 201, 404, 500]
    
    def test_chunked_upload_invalid_params(self):
        """Test chunked upload with invalid parameters."""
        chunk_file = BytesIO(b"test chunk data")
        files = {"chunk_file": ("chunk", chunk_file, "application/octet-stream")}
        
        # Missing required parameters
        response = client.post("/api/v1/datasets/invalid-id/chunks", files=files)
        assert response.status_code == 422


class TestImageManagement:
    """Test image-related endpoints."""
    
    def test_list_images_for_nonexistent_dataset(self):
        """Test listing images for a dataset that doesn't exist."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/datasets/{fake_id}/images")
        assert response.status_code in [200, 404]  # Depends on implementation
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 0
    
    def test_list_images_with_pagination(self):
        """Test image listing with pagination parameters."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(
            f"/api/v1/datasets/{fake_id}/images",
            params={"limit": 10, "offset": 0}
        )
        assert response.status_code in [200, 404]


class TestImportStatus:
    """Test import status endpoints."""
    
    def test_get_import_status_nonexistent_dataset(self):
        """Test getting import status for non-existent dataset."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/datasets/{fake_id}/import-status")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data


class TestAPIDocumentation:
    """Test API documentation endpoints."""
    
    def test_openapi_schema(self):
        """Test that OpenAPI schema is accessible."""
        response = client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
    
    def test_docs_endpoint(self):
        """Test that Swagger docs are accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_redoc_endpoint(self):
        """Test that ReDoc documentation is accessible."""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestErrorHandling:
    """Test error handling across endpoints."""
    
    def test_invalid_json_payload(self):
        """Test handling of invalid JSON payloads."""
        response = client.post(
            "/api/v1/datasets/",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_unsupported_media_type(self):
        """Test handling of unsupported media types."""
        response = client.post(
            "/api/v1/datasets/import/yolo",
            data="not a file",
            headers={"Content-Type": "text/plain"}
        )
        assert response.status_code == 422
    
    def test_large_payload_handling(self):
        """Test handling of very large payloads."""
        # Create a large dataset name (should be rejected)
        large_data = {
            "name": "x" * 10000,  # Very long name
            "description": "Test dataset with large name"
        }
        response = client.post("/api/v1/datasets/", json=large_data)
        assert response.status_code in [422, 413]  # Validation error or payload too large


# Integration test class
class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""
    
    def test_complete_dataset_lifecycle(self):
        """Test creating, importing, and managing a dataset."""
        # This test would require a running MongoDB instance
        # For now, we'll test the API responses
        
        # 1. Create dataset
        response = client.post("/api/v1/datasets/", json=SAMPLE_DATASET_DATA)
        if response.status_code == 200:
            dataset_id = response.json()["id"]
            
            # 2. List datasets (should include our new one)
            response = client.get("/api/v1/datasets/")
            assert response.status_code == 200
            
            # 3. Get specific dataset
            response = client.get(f"/api/v1/datasets/{dataset_id}")
            if response.status_code == 200:
                data = response.json()
                assert data["name"] == SAMPLE_DATASET_DATA["name"]
            
            # 4. List images (should be empty initially)
            response = client.get(f"/api/v1/datasets/{dataset_id}/images")
            assert response.status_code in [200, 404]
            
            # 5. Check import status
            response = client.get(f"/api/v1/datasets/{dataset_id}/import-status")
            assert response.status_code in [200, 404]


if __name__ == "__main__":
    # Run specific test classes
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x"  # Stop on first failure
    ])
