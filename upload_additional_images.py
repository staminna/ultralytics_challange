#!/usr/bin/env python3
"""
Upload additional London hotel images from sample_images folder.
These are raw images without YOLO labels.
"""

import requests
import os
from pathlib import Path
import time

API_BASE = "http://localhost:8000/api/v1"
IMAGES_PATH = Path("backend/datasets/sample_images/london_hotels")

def create_raw_images_dataset():
    """Create a dataset for raw images without labels."""
    print("🔍 Creating dataset for additional London hotel images...")
    
    url = f"{API_BASE}/datasets"
    data = {
        "name": "London Hotels - Additional Images",
        "description": "Additional 46 London hotel images without YOLO labels for annotation",
        "dataset_type": "image_classification"
    }
    
    response = requests.post(url, json=data)
    if response.status_code == 201:
        dataset = response.json()
        print(f"✅ Dataset created: {dataset['id']}")
        return dataset['id']
    else:
        print(f"❌ Failed to create dataset: {response.status_code}")
        print(response.text)
        return None

def upload_images_to_dataset(dataset_id):
    """Upload all images from the sample_images folder to the dataset."""
    if not IMAGES_PATH.exists():
        print(f"❌ Images path not found: {IMAGES_PATH}")
        return
    
    image_files = list(IMAGES_PATH.glob("*.jpg"))
    print(f"📁 Found {len(image_files)} images to upload")
    
    uploaded_count = 0
    failed_count = 0
    
    for i, img_path in enumerate(image_files, 1):
        print(f"📤 Uploading {i}/{len(image_files)}: {img_path.name}")
        
        try:
            url = f"{API_BASE}/datasets/{dataset_id}/images"
            
            with open(img_path, "rb") as f:
                files = {"image": (img_path.name, f, "image/jpeg")}
                response = requests.post(url, files=files)
            
            if response.status_code == 201:
                uploaded_count += 1
                print(f"   ✅ Uploaded successfully")
            else:
                failed_count += 1
                print(f"   ❌ Failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            failed_count += 1
            print(f"   ❌ Error: {str(e)}")
        
        # Small delay to avoid overwhelming the server
        time.sleep(0.1)
    
    print(f"\n📊 Upload Summary:")
    print(f"   ✅ Uploaded: {uploaded_count}")
    print(f"   ❌ Failed: {failed_count}")
    print(f"   📝 Total: {len(image_files)}")
    
    return uploaded_count

def verify_dataset(dataset_id):
    """Verify the dataset was created and images were uploaded."""
    print(f"\n🔍 Verifying dataset {dataset_id}...")
    
    # Get dataset details
    url = f"{API_BASE}/datasets/{dataset_id}"
    response = requests.get(url)
    
    if response.status_code == 200:
        dataset = response.json()
        print(f"✅ Dataset: {dataset['name']}")
        print(f"   📊 Images: {dataset.get('image_count', 0)}")
        print(f"   📝 Description: {dataset['description']}")
        
        # List some images
        images_url = f"{API_BASE}/datasets/{dataset_id}/images"
        images_response = requests.get(images_url)
        
        if images_response.status_code == 200:
            images = images_response.json()
            print(f"   🖼️  First 5 images:")
            for img in images.get('images', [])[:5]:
                print(f"      - {img.get('filename', 'N/A')} ({img.get('width', 0)}x{img.get('height', 0)})")
        
        return True
    else:
        print(f"❌ Failed to verify dataset: {response.status_code}")
        return False

def main():
    """Main function to upload additional images."""
    print("🚀 London Hotels - Additional Images Upload")
    print("=" * 50)
    
    # Check if images directory exists
    if not IMAGES_PATH.exists():
        print(f"❌ Images directory not found: {IMAGES_PATH}")
        return
    
    # Create dataset
    dataset_id = create_raw_images_dataset()
    if not dataset_id:
        return
    
    # Upload images
    uploaded_count = upload_images_to_dataset(dataset_id)
    
    if uploaded_count > 0:
        # Verify upload
        time.sleep(2)  # Wait a bit for processing
        verify_dataset(dataset_id)
        
        print(f"\n🎉 Successfully uploaded {uploaded_count} additional London hotel images!")
        print(f"   Dataset ID: {dataset_id}")
        print(f"   API URL: {API_BASE}/datasets/{dataset_id}")
    else:
        print("\n❌ No images were uploaded successfully")

if __name__ == "__main__":
    main()
