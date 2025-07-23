#!/usr/bin/env python3
"""
Test Chunked Upload with Small File
Tests the chunked upload functionality with a small sample file
"""

import requests
import os
import tempfile
import zipfile
import uuid
import time
from pathlib import Path

def create_test_yolo_dataset() -> str:
    """Create a small test YOLO dataset for chunked upload testing"""
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    dataset_dir = os.path.join(temp_dir, "test_yolo_chunked")
    os.makedirs(dataset_dir)
    
    # Create images directory
    images_dir = os.path.join(dataset_dir, "images")
    os.makedirs(images_dir)
    
    # Create labels directory
    labels_dir = os.path.join(dataset_dir, "labels")
    os.makedirs(labels_dir)
    
    # Create sample image files (dummy data)
    for i in range(5):
        image_path = os.path.join(images_dir, f"test_image_{i:03d}.jpg")
        with open(image_path, 'wb') as f:
            # Write some dummy image data (1KB each)
            f.write(b'FAKE_JPG_DATA' * 80)  # ~1KB
            
        # Create corresponding label file
        label_path = os.path.join(labels_dir, f"test_image_{i:03d}.txt")
        with open(label_path, 'w') as f:
            f.write(f"0 0.5 0.5 0.3 0.4\n")  # class_id x_center y_center width height
    
    # Create classes.txt
    classes_path = os.path.join(dataset_dir, "classes.txt")
    with open(classes_path, 'w') as f:
        f.write("test_object\n")
    
    # Create data.yaml
    data_yaml_path = os.path.join(dataset_dir, "data.yaml")
    with open(data_yaml_path, 'w') as f:
        f.write(f"""
train: images
val: images
test: images

nc: 1
names: ['test_object']
""")
    
    # Create ZIP file
    zip_path = os.path.join(temp_dir, "test_chunked_dataset.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dataset_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, dataset_dir)
                zipf.write(file_path, arc_name)
    
    return zip_path

def create_dataset_for_chunked_upload(dataset_name: str) -> str:
    """Create a dataset first to get dataset_id for chunked upload"""
    try:
        data = {
            "name": dataset_name,
            "description": "Test dataset for chunked upload functionality",
            "format": "YOLO"
        }
        
        response = requests.post(
            "http://localhost:8000/api/v1/datasets/",
            json=data,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            dataset_id = result.get('id')
            print(f"✅ Dataset created: {dataset_id}")
            return dataset_id
        else:
            print(f"❌ Dataset creation failed: {response.status_code}")
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating dataset: {e}")
        return None

def upload_file_in_chunks(file_path: str, dataset_id: str, chunk_size: int = 1024) -> bool:
    """Upload a file in small chunks for testing"""
    
    file_size = os.path.getsize(file_path)
    total_chunks = (file_size + chunk_size - 1) // chunk_size  # Ceiling division
    upload_id = str(uuid.uuid4())  # Generate unique upload ID
    
    print(f"📊 File size: {file_size} bytes")
    print(f"📦 Chunk size: {chunk_size} bytes")
    print(f"🔢 Total chunks: {total_chunks}")
    print(f"🆔 Upload ID: {upload_id}")
    
    try:
        with open(file_path, 'rb') as f:
            for chunk_number in range(total_chunks):
                # Read chunk data
                chunk_data = f.read(chunk_size)
                if not chunk_data:
                    break
                
                print(f"⏳ Uploading chunk {chunk_number + 1}/{total_chunks} ({len(chunk_data)} bytes)...")
                
                # Prepare multipart form data
                files = {
                    'chunk_file': (f'chunk_{chunk_number}', chunk_data, 'application/octet-stream')
                }
                
                # Parameters as query parameters
                params = {
                    'dataset_id': dataset_id,
                    'upload_id': upload_id,
                    'chunk_number': chunk_number,
                    'total_chunks': total_chunks
                }
                
                # Upload chunk
                response = requests.post(
                    "http://localhost:8000/api/v1/datasets/import/yolo/chunk",
                    files=files,
                    params=params,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Chunk {chunk_number + 1} uploaded successfully")
                    
                    # Check if this was the final chunk
                    if chunk_number == total_chunks - 1:
                        print("🎉 All chunks uploaded! Processing dataset...")
                        return True
                        
                else:
                    print(f"❌ Chunk {chunk_number + 1} upload failed: {response.status_code}")
                    print(f"Error: {response.text}")
                    return False
                
                # Small delay between chunks
                time.sleep(0.1)
                
        return True
        
    except Exception as e:
        print(f"❌ Error during chunked upload: {e}")
        return False

def test_chunked_upload():
    """Test the chunked upload functionality"""
    
    print("======================================================================")
    print("  🧪 Testing Chunked Upload Functionality")
    print("======================================================================")
    
    # Step 1: Create test dataset
    print("\n📋 Step 1: Creating test YOLO dataset...")
    test_zip_path = create_test_yolo_dataset()
    print(f"✅ Test dataset created: {test_zip_path}")
    print(f"📊 File size: {os.path.getsize(test_zip_path)} bytes")
    
    # Step 2: Create dataset in API
    dataset_name = f"Test Chunked Upload - {int(time.time())}"
    print(f"\n📋 Step 2: Creating dataset in API...")
    dataset_id = create_dataset_for_chunked_upload(dataset_name)
    
    if not dataset_id:
        print("❌ Failed to create dataset. Aborting test.")
        return False
    
    # Step 3: Upload in small chunks (1KB chunks for testing)
    print(f"\n📦 Step 3: Uploading file in 1KB chunks...")
    success = upload_file_in_chunks(
        file_path=test_zip_path,
        dataset_id=dataset_id,
        chunk_size=1024  # 1KB chunks for testing
    )
    
    if success:
        print("\n✅ Chunked upload test completed successfully!")
        print(f"🆔 Dataset ID: {dataset_id}")
        print(f"🔗 View dataset: http://localhost:8000/docs#/datasets/get_dataset_api_v1_datasets__dataset_id__get")
        
        # Clean up test file
        os.unlink(test_zip_path)
        print("🧹 Test file cleaned up")
        
        return True
    else:
        print("\n❌ Chunked upload test failed")
        return False

if __name__ == "__main__":
    print("🧪 Chunked Upload Test")
    print("=" * 50)
    
    # Check if API is accessible
    try:
        response = requests.get("http://localhost:8000/api/v1/datasets/", timeout=10)
        if response.status_code == 200:
            print("✅ API is accessible")
        else:
            print(f"❌ API error: {response.status_code}")
            exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("Make sure the backend service is running: docker-compose up -d")
        exit(1)
    
    # Run the test
    success = test_chunked_upload()
    
    if success:
        print("\n🎉 Chunked upload functionality is working correctly!")
        print("You can now use import_large_dataset.py for large files.")
    else:
        print("\n⚠️  Chunked upload test failed.")
        print("Check the backend logs: docker-compose logs backend")
