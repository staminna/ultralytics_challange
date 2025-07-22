#!/usr/bin/env python3
"""
Debug script to test YOLO dataset upload and see detailed logs.
"""

import requests
import json
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
DATASET_ZIP = Path("backend/datasets/london_hotels_yolo.zip")

def test_upload():
    """Test uploading the smallest dataset with detailed logging."""
    print("🔍 YOLO Upload Debug Test")
    print("=" * 40)
    
    # Check server
    try:
        response = requests.get(f"{API_BASE_URL}/datasets/", timeout=5)
        print(f"✅ Server status: {response.status_code}")
        datasets = response.json().get('datasets', [])
        print(f"📊 Current datasets: {len(datasets)}")
    except Exception as e:
        print(f"❌ Server error: {e}")
        return
    
    if not DATASET_ZIP.exists():
        print(f"❌ Dataset not found: {DATASET_ZIP}")
        return
    
    print(f"📦 Testing upload: {DATASET_ZIP.name} ({DATASET_ZIP.stat().st_size / 1024:.1f} KB)")
    
    # Upload dataset
    try:
        url = f"{API_BASE_URL}/datasets/import/yolo"
        
        with open(DATASET_ZIP, 'rb') as f:
            files = {'zip_file': (DATASET_ZIP.name, f, 'application/zip')}
            data = {'dataset_name': 'Debug Test Dataset'}
            
            print("🚀 Uploading...")
            response = requests.post(url, files=files, data=data, timeout=120)
            
        print(f"📡 Response status: {response.status_code}")
        print(f"📄 Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Upload successful!")
            print(f"📋 Response data:")
            print(json.dumps(result, indent=2))
            
            dataset_id = result.get('id')
            if dataset_id:
                print(f"\n🔍 Checking dataset details...")
                
                # Get dataset details
                detail_response = requests.get(f"{API_BASE_URL}/datasets/{dataset_id}")
                if detail_response.status_code == 200:
                    details = detail_response.json()
                    print(f"📊 Dataset details:")
                    print(f"   Name: {details.get('name')}")
                    print(f"   Images: {details.get('image_count', 0)}")
                    print(f"   Created: {details.get('created_at')}")
                
                # Get images list
                images_response = requests.get(f"{API_BASE_URL}/datasets/{dataset_id}/images")
                if images_response.status_code == 200:
                    images = images_response.json().get('images', [])
                    print(f"🖼️  Images found: {len(images)}")
                    for i, img in enumerate(images[:3]):  # Show first 3
                        print(f"   {i+1}. {img.get('filename')} - Labels: {len(img.get('labels', []))}")
                else:
                    print(f"❌ Failed to get images: {images_response.status_code}")
                    print(f"   Response: {images_response.text}")
        else:
            print("❌ Upload failed!")
            print(f"📄 Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Upload error: {e}")

if __name__ == "__main__":
    test_upload()
