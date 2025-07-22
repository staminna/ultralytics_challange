#!/usr/bin/env python3
"""
Upload London Hotels YOLO dataset to the cloud via API.
"""

import requests
import zipfile
import os
from pathlib import Path
import tempfile
import shutil

# API configuration
API_BASE = "http://localhost:8000/api/v1"
DATASET_PATH = Path("backend/datasets/london_hotels_yolo")

def create_zip_from_yolo_dataset():
    """Create a ZIP file from the YOLO dataset directory."""
    print("📦 Creating ZIP file from YOLO dataset...")
    
    # Create temporary ZIP file
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    temp_zip.close()
    
    with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add all files from the dataset directory
        for root, dirs, files in os.walk(DATASET_PATH):
            for file in files:
                file_path = Path(root) / file
                # Calculate relative path from dataset root
                relative_path = file_path.relative_to(DATASET_PATH)
                zipf.write(file_path, relative_path)
                print(f"  Added: {relative_path}")
    
    print(f"✅ ZIP file created: {temp_zip.name}")
    return temp_zip.name

def upload_yolo_dataset():
    """Upload the London Hotels YOLO dataset via API."""
    print("🚀 Starting London Hotels dataset upload...")
    
    # Check if API is running
    try:
        response = requests.get("http://localhost:8000/")
        print(f"API health check: {response.status_code}")
        if response.status_code != 200:
            print("❌ API is not responding properly. Make sure the server is running.")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Start the server with:")
        print("   cd backend && uvicorn app.main:app --reload")
        return False
    
    # Check if the correct endpoint exists
    try:
        response = requests.get(f"{API_BASE}/datasets/")
        print(f"Datasets endpoint check: {response.status_code}")
    except Exception as e:
        print(f"❌ API endpoints not available: {e}")
        return False
    
    # Create ZIP file
    zip_path = create_zip_from_yolo_dataset()
    
    try:
        # Class names as list
        class_names = [
            'backpack', 'bed', 'bench', 'boat', 'book', 'chair', 
            'couch', 'dining table', 'person', 'tv', 'umbrella', 'wine glass'
        ]
        
        print("📤 Uploading dataset to cloud...")
        print(f"   Dataset: London Hotels")
        print(f"   Classes: {', '.join(class_names)}")
        print(f"   Endpoint: {API_BASE}/datasets/import/yolo")
        
        # Upload the ZIP file with proper form data
        with open(zip_path, 'rb') as zip_file:
            files = {'zip_file': ('london_hotels_yolo.zip', zip_file, 'application/zip')}
            
            # Prepare form data with multiple class_names fields
            data = [
                ('dataset_name', 'London Hotels'),
                ('description', 'London hotel images with YOLO object detection labels (12 classes)'),
            ]
            
            # Add each class name as a separate form field
            for class_name in class_names:
                data.append(('class_names', class_name))
            
            response = requests.post(
                f"{API_BASE}/datasets/import/yolo",
                data=data,
                files=files,
                timeout=300  # 5 minutes timeout for large uploads
            )
        
        print(f"Upload response status: {response.status_code}")
        print(f"Upload response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Dataset uploaded successfully!")
            print(f"   Dataset ID: {result.get('id')}")
            print(f"   Dataset Name: {result.get('name')}")
            print(f"   Created: {result.get('created_at')}")
            return True
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Error: {response.text}")
            
            # Try to parse error details
            try:
                error_detail = response.json()
                print(f"   Error detail: {error_detail}")
            except:
                pass
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Upload timed out. The dataset might be too large.")
        return False
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        return False
    finally:
        # Clean up temporary ZIP file
        if os.path.exists(zip_path):
            os.unlink(zip_path)
            print("🧹 Cleaned up temporary files")

def list_datasets():
    """List all datasets to verify upload."""
    print("\n📋 Listing all datasets...")
    try:
        response = requests.get(f"{API_BASE}/datasets/")
        if response.status_code == 200:
            datasets = response.json()
            if datasets.get('datasets'):
                for dataset in datasets['datasets']:
                    print(f"   📁 {dataset['name']} (ID: {dataset['id']})")
                    print(f"      Images: {dataset.get('image_count', 0)}")
                    print(f"      Created: {dataset.get('created_at', 'N/A')}")
            else:
                print("   No datasets found")
        else:
            print(f"❌ Failed to list datasets: {response.status_code}")
    except Exception as e:
        print(f"❌ Error listing datasets: {str(e)}")

if __name__ == "__main__":
    print("🏨 London Hotels Dataset Upload Tool")
    print("=" * 50)
    
    # Upload the dataset
    success = upload_yolo_dataset()
    
    if success:
        # List datasets to confirm
        list_datasets()
        print("\n🎉 Upload completed successfully!")
        print("\nNext steps:")
        print("1. View datasets: GET http://localhost:8000/api/v1/datasets/")
        print("2. View images: GET http://localhost:8000/api/v1/datasets/{dataset_id}/images")
        print("3. Access API docs: http://localhost:8000/docs")
    else:
        print("\n❌ Upload failed. Please check the error messages above.")
        print("\nTroubleshooting:")
        print("1. Make sure the API server is running: cd backend && uvicorn app.main:app --reload")
        print("2. Check server logs for any errors")
        print("3. Verify API docs at: http://localhost:8000/docs")
