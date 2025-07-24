#!/usr/bin/env python3
"""
Large Dataset Import Handler for COCO Train 2017 (19GB)
Handles chunked upload for very large datasets using proper chunked upload API
"""

import requests
import os
import json
import uuid
import time
from pathlib import Path
from typing import Optional

def create_dataset_for_chunked_upload(dataset_name: str, description: str = "") -> Optional[str]:
    """Create a dataset first to get dataset_id for chunked upload"""
    try:
        data = {
            "name": dataset_name,
            "description": description or f"Large YOLO dataset imported via chunked upload",
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

def upload_file_in_chunks(file_path: str, dataset_id: str, chunk_size: int = 10 * 1024 * 1024) -> bool:
    """Upload a large file in chunks using the /chunk endpoint"""
    
    file_size = os.path.getsize(file_path)
    total_chunks = (file_size + chunk_size - 1) // chunk_size  # Ceiling division
    upload_id = str(uuid.uuid4())  # Generate unique upload ID
    
    print(f"📊 File size: {file_size / (1024**3):.2f} GB")
    print(f"📦 Chunk size: {chunk_size / (1024**2):.1f} MB")
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
                    timeout=300  # 5 minute timeout per chunk
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
                
                # Small delay between chunks to avoid overwhelming the server
                time.sleep(0.5)
                
        return True
        
    except Exception as e:
        print(f"❌ Error during chunked upload: {e}")
        return False

def import_large_dataset():
    """Import the 19GB COCO dataset using proper chunked upload"""
    
    dataset_path = "/Users/jorgenunes/2026/datasets/coco-train2017-images.zip"
    # Add timestamp to make name unique
    import time
    timestamp = int(time.time())
    dataset_name = f"COCO Train 2017 - Complete Dataset (19GB) - {timestamp}"
    
    if not os.path.exists(dataset_path):
        print(f"❌ Dataset not found: {dataset_path}")
        print("💡 You can download it using:")
        print("   wget http://images.cocodataset.org/zips/train2017.zip")
        return
    
    file_size_gb = os.path.getsize(dataset_path) / (1024**3)
    print(f"📁 Dataset: {os.path.basename(dataset_path)}")
    print(f"📊 Size: {file_size_gb:.2f} GB")
    print(f"🏷️  Name: {dataset_name}")
    
    print("\n======================================================================")
    print("  🚀 Large Dataset Chunked Upload Process")
    print("======================================================================")
    
    # Step 1: Create dataset
    print("\n📋 Step 1: Creating dataset...")
    dataset_id = create_dataset_for_chunked_upload(
        dataset_name=dataset_name,
        description=f"Large YOLO dataset ({file_size_gb:.2f} GB) imported via chunked upload"
    )
    
    if not dataset_id:
        print("❌ Failed to create dataset. Aborting.")
        return None
    
    # Step 2: Upload file in chunks
    print(f"\n📦 Step 2: Uploading file in chunks...")
    print("⚠️  This may take a while due to the large file size...")
    
    success = upload_file_in_chunks(
        file_path=dataset_path,
        dataset_id=dataset_id,
        chunk_size=10 * 1024 * 1024  # 10MB chunks
    )
    
    if success:
        print("\n✅ Large dataset import completed successfully!")
        print(f"🆔 Dataset ID: {dataset_id}")
        print(f"📊 Monitor progress at: http://localhost:8000/api/v1/datasets/{dataset_id}/import/status")
        print(f"🔗 View dataset: http://localhost:8000/docs#/datasets/get_dataset_api_v1_datasets__dataset_id__get")
        
        return {
            'id': dataset_id,
            'name': dataset_name,
            'status': 'uploaded',
            'file_size_gb': file_size_gb
        }
    else:
        print("\n❌ Large dataset import failed")
        print(f"🗑️  You may want to delete the partially created dataset: {dataset_id}")
        return None

def check_import_status(dataset_id):
    """Check the status of a dataset import"""
    try:
        response = requests.get(f"http://localhost:8000/api/v1/datasets/{dataset_id}/import/status")
        if response.status_code == 200:
            result = response.json()
            print(f"Status: {result.get('status', 'Unknown')}")
            print(f"Progress: {result.get('progress', 0)}%")
            return result
        else:
            print(f"❌ Status check failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Large Dataset Import Handler")
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
    
    # Import the large dataset
    result = import_large_dataset()
    
    if result:
        print("\n🎉 Large dataset import completed successfully!")
        print("The dataset is now available in your SaaS annotation service.")
    else:
        print("\n⚠️  Import may be processing in background or failed.")
        print("Check the backend logs: docker-compose logs backend")
