#!/usr/bin/env python3
"""
Test script to verify the YOLO import endpoint returns a concise response.
"""

import requests
import json
from pathlib import Path

def test_import_response():
    """Test that the import endpoint returns a summary response, not verbose dataset."""
    
    # Find a small test dataset
    datasets_dir = Path("backend/datasets")
    test_files = list(datasets_dir.glob("**/*.zip"))
    
    if not test_files:
        print("❌ No test datasets found in backend/datasets/")
        print("Please download a dataset first with: python scripts/download_datasets.py download coco8")
        return
    
    test_file = test_files[0]
    print(f"🧪 Testing import with: {test_file.name}")
    
    # Test the import endpoint
    url = "http://localhost:8000/api/v1/datasets/import/yolo"
    
    try:
        with open(test_file, 'rb') as f:
            files = {'file': (test_file.name, f, 'application/zip')}
            data = {'dataset_name': f'test_response_{test_file.stem}'}
            
            print("📤 Uploading dataset...")
            response = requests.post(url, files=files, data=data, timeout=300)
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ Import successful!")
            print(f"📊 Response size: {len(response.text)} characters")
            print("\n📋 Response summary:")
            print(f"  • Dataset ID: {result.get('id')}")
            print(f"  • Name: {result.get('name')}")
            print(f"  • Format: {result.get('format')}")
            print(f"  • Status: {result.get('processing_status')}")
            print(f"  • Images: {result.get('images_count')}")
            print(f"  • Labels: {result.get('labels_count')}")
            print(f"  • Processed: {result.get('processed_images')}")
            print(f"  • Classes: {result.get('classes_count')}")
            print(f"  • Original file: {result.get('original_filename')}")
            
            # Check if response contains image arrays (should not)
            if 'images' in result and isinstance(result['images'], list):
                print(f"⚠️  Response still contains images array with {len(result['images'])} items")
            else:
                print("✅ Response is concise - no verbose image arrays")
                
        else:
            print(f"❌ Import failed with status {response.status_code}")
            print(f"Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_import_response()
