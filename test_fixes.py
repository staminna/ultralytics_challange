#!/usr/bin/env python3
"""
Quick test script to verify the fixes for at least 90% test coverage.
"""

import requests
import time

API_BASE = "http://localhost:8000/api/v1"

def test_uuid_validation():
    """Test that invalid UUIDs return 404 instead of 400."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    
    # Test dataset retrieval
    response = requests.get(f"{API_BASE}/datasets/{fake_id}")
    print(f"Dataset retrieval with fake UUID: {response.status_code} (expected: 404)")
    
    # Test dataset deletion
    response = requests.delete(f"{API_BASE}/datasets/{fake_id}")
    print(f"Dataset deletion with fake UUID: {response.status_code} (expected: 404)")
    
    # Test image listing
    response = requests.get(f"{API_BASE}/datasets/{fake_id}/images")
    print(f"Image listing with fake UUID: {response.status_code} (expected: 404)")
    
    # Test import status
    response = requests.get(f"{API_BASE}/datasets/{fake_id}/import-status")
    print(f"Import status with fake UUID: {response.status_code} (expected: 404)")

def test_dataset_creation():
    """Test dataset creation with unique names."""
    timestamp = int(time.time())
    dataset_data = {
        "name": f"Test Dataset {timestamp}",
        "description": "Test dataset for validation",
        "format": "yolo"
    }
    
    response = requests.post(f"{API_BASE}/datasets/", json=dataset_data)
    print(f"Dataset creation: {response.status_code} (expected: 200)")
    
    if response.status_code == 200:
        dataset_id = response.json().get("id")
        print(f"Created dataset ID: {dataset_id}")
        return dataset_id
    return None

def test_image_upload(dataset_id):
    """Test image upload to dataset."""
    if not dataset_id:
        print("Skipping image upload test - no dataset ID")
        return
        
    # Create a simple test image file
    test_image_data = b"fake image data"
    files = {"image": ("test.jpg", test_image_data, "image/jpeg")}
    
    response = requests.post(f"{API_BASE}/datasets/{dataset_id}/images", files=files)
    print(f"Image upload: {response.status_code} (expected: 200 or 404)")

def main():
    """Run all tests."""
    print("🧪 Testing fixes for at least 90% coverage")
    print("=" * 40)
    
    print("\n1. Testing UUID validation fixes:")
    test_uuid_validation()
    
    print("\n2. Testing dataset creation:")
    dataset_id = test_dataset_creation()
    
    print("\n3. Testing image upload:")
    test_image_upload(dataset_id)
    
    print("\n✅ Test script completed!")

if __name__ == "__main__":
    main()
