#!/usr/bin/env python3
"""Test script for YOLO dataset import with train/val subdirectories."""

import json
import os
import time
import zipfile
from pathlib import Path

import requests

# Configuration
API_URL = "http://localhost:8000/api/v1"
DATASET_DIR = "backend/datasets"
OUTPUT_ZIP = "test_london_hotels_yolo.zip"
DATASET_NAME = "London Hotels Test Import"
DATASET_DESC = "Test import of London Hotels dataset with train/val subdirectories"

def create_zip_from_directory(directory_path, output_zip):
    """Create a ZIP file from a directory."""
    print(f"Creating ZIP file from {directory_path}...")
    abs_directory = os.path.abspath(directory_path)
    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(abs_directory):
            for file in files:
                file_path = os.path.join(root, file)
                # Calculate relative path to preserve directory structure
                rel_path = os.path.relpath(file_path, os.path.dirname(abs_directory))
                zipf.write(file_path, rel_path)
    
    zip_size = os.path.getsize(output_zip) / (1024 * 1024)  # Size in MB
    print(f"✅ Created {output_zip} ({zip_size:.2f} MB)")
    return output_zip

def upload_dataset(zip_path, dataset_name, dataset_desc):
    """Upload a dataset to the API."""
    print(f"Uploading dataset {dataset_name}...")
    
    url = f"{API_URL}/datasets/import/yolo"
    
    with open(zip_path, 'rb') as zip_file:
        files = {'zip_file': (os.path.basename(zip_path), zip_file, 'application/zip')}
        data = {
            'dataset_name': dataset_name,
            'description': dataset_desc
        }
        
        try:
            response = requests.post(url, files=files, data=data)
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Upload successful! Dataset ID: {result.get('id')}")
                return result
            else:
                print(f"❌ Upload failed with status code {response.status_code}")
                print(f"Response: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error during upload: {str(e)}")
            return None

def check_dataset_status(dataset_id):
    """Check the status of a dataset import."""
    print(f"Checking status of dataset {dataset_id}...")
    
    url = f"{API_URL}/datasets/import/status/{dataset_id}"
    
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                status_data = response.json()
                status = status_data.get('status')
                progress = status_data.get('progress', 0)
                
                print(f"Status: {status}, Progress: {progress}%")
                
                if status == 'ready':
                    print("✅ Dataset import completed successfully!")
                    return True
                elif status == 'error':
                    print(f"❌ Dataset import failed: {status_data.get('error_message')}")
                    return False
                
                # Wait before checking again
                time.sleep(2)
                attempt += 1
            else:
                print(f"❌ Failed to check status: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error checking status: {str(e)}")
            return False
    
    print("❌ Timeout waiting for dataset import to complete")
    return False

def get_dataset_images(dataset_id):
    """Get images for a dataset."""
    print(f"Getting images for dataset {dataset_id}...")
    
    url = f"{API_URL}/datasets/{dataset_id}/images"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            result = response.json()
            images = result.get('images', [])
            total = result.get('total', 0)
            
            print(f"✅ Found {total} images in dataset")
            
            # Count images with labels
            images_with_labels = [img for img in images if img.get('labels', [])]
            print(f"📊 Images with labels: {len(images_with_labels)}/{len(images)}")
            
            # Print sample of images
            print("\nSample images:")
            for img in images[:5]:
                filename = img.get('filename', 'unknown')
                label_count = len(img.get('labels', []))
                print(f"  • {filename}: {label_count} labels")
            
            return images
        else:
            print(f"❌ Failed to get images: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error getting images: {str(e)}")
        return []

def analyze_dataset_structure(directory_path=None):
    """Analyze the structure of the dataset directory."""
    if directory_path is None:
        directory_path = DATASET_DIR
    dataset_path = Path(directory_path)
    
    if not dataset_path.exists():
        print(f"❌ Dataset directory {directory_path} not found!")
        return
    
    print(f"Analyzing dataset structure in {directory_path}...")
    
    # Count images
    images_dir = dataset_path / "images"
    images_train_dir = images_dir / "train"
    
    all_images = []
    if images_dir.exists():
        all_images.extend([f for f in images_dir.glob("*.jpg") if f.is_file()])
        all_images.extend([f for f in images_dir.glob("*.jpeg") if f.is_file()])
        all_images.extend([f for f in images_dir.glob("*.png") if f.is_file()])
    
    train_images = []
    if images_train_dir.exists():
        train_images.extend([f for f in images_train_dir.glob("*.jpg") if f.is_file()])
        train_images.extend([f for f in images_train_dir.glob("*.jpeg") if f.is_file()])
        train_images.extend([f for f in images_train_dir.glob("*.png") if f.is_file()])
    
    # Count labels
    labels_dir = dataset_path / "labels"
    labels_train_dir = labels_dir / "train"
    
    all_labels = []
    if labels_dir.exists():
        all_labels.extend([f for f in labels_dir.glob("*.txt") if f.is_file()])
    
    train_labels = []
    if labels_train_dir.exists():
        train_labels.extend([f for f in labels_train_dir.glob("*.txt") if f.is_file()])
    
    # Check for metadata files
    classes_file = dataset_path / "classes.txt"
    data_yaml = dataset_path / "data.yaml"
    
    print("\n📊 Dataset Structure Analysis:")
    print(f"  • Root images: {len(all_images) - len(train_images)}")
    print(f"  • Train images: {len(train_images)}")
    print(f"  • Total images: {len(all_images)}")
    print(f"  • Root labels: {len(all_labels) - len(train_labels)}")
    print(f"  • Train labels: {len(train_labels)}")
    print(f"  • Total labels: {len(all_labels)}")
    print(f"  • classes.txt: {'✅ Found' if classes_file.exists() else '❌ Not found'}")
    print(f"  • data.yaml: {'✅ Found' if data_yaml.exists() else '❌ Not found'}")
    
    # Read class names if available
    if classes_file.exists():
        with open(classes_file, 'r') as f:
            classes = [line.strip() for line in f.readlines()]
        print(f"  • Classes: {', '.join(classes)}")
    
    return {
        "root_images": len(all_images) - len(train_images),
        "train_images": len(train_images),
        "total_images": len(all_images),
        "root_labels": len(all_labels) - len(train_labels),
        "train_labels": len(train_labels),
        "total_labels": len(all_labels)
    }

def main():
    """Main function to test YOLO import."""
    print("🔍 YOLO Import Test")
    print("=" * 60)
    
    # Analyze dataset structure
    structure = analyze_dataset_structure()
    
    # Create ZIP file
    zip_path = create_zip_from_directory(DATASET_DIR, OUTPUT_ZIP)
    
    # Upload dataset
    result = upload_dataset(zip_path, DATASET_NAME, DATASET_DESC)
    if not result:
        return
    
    dataset_id = result.get('id')
    
    # Check status
    if check_dataset_status(dataset_id):
        # Get images
        images = get_dataset_images(dataset_id)
        
        # Verify results
        if images:
            print("\n🔍 Verification:")
            print(f"  • Expected total images: {structure['total_images']}")
            print(f"  • Actual images processed: {len(images)}")
            print(f"  • Expected images with labels: {structure['total_labels']}")
            
            images_with_labels = [img for img in images if img.get('labels', [])]
            print(f"  • Actual images with labels: {len(images_with_labels)}")
            
            if len(images) == structure['total_images']:
                print("✅ All images were processed correctly!")
            else:
                print("❌ Not all images were processed!")
            
            if len(images_with_labels) == structure['total_labels']:
                print("✅ All labels were processed correctly!")
            else:
                print("❌ Not all labels were processed!")

if __name__ == "__main__":
    main()
