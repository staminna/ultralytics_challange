#!/usr/bin/env python3
"""
Quick Verification Script for YOLO Import Service Fix

This script specifically checks if the YOLO import service is correctly handling
images in train/val subdirectories and their corresponding labels.
"""

import json
import os
import time
import zipfile
from pathlib import Path

import requests
from tabulate import tabulate

# Configuration
API_URL = "http://localhost:8000/api/v1"
DATASET_DIR = "50_items_yolo_london_hotels"
OUTPUT_ZIP = "verification_test_dataset.zip"
DATASET_NAME = "Verification Test Dataset"
DATASET_DESC = "Testing YOLO import fix for train/val subdirectories"

def analyze_dataset_structure(dataset_dir):
    """Analyze the structure of the dataset directory."""
    dataset_path = Path(dataset_dir)
    
    if not dataset_path.exists():
        print(f"❌ Dataset directory {dataset_dir} not found!")
        return {}
    
    print(f"Analyzing dataset structure in {dataset_dir}...")
    
    # Count images
    images_dir = dataset_path / "images"
    images_train_dir = images_dir / "train"
    images_val_dir = images_dir / "val"
    
    all_images = []
    root_images = []
    train_images = []
    val_images = []
    
    if images_dir.exists():
        root_images = list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.jpeg")) + list(images_dir.glob("*.png"))
        all_images.extend(root_images)
    
    if images_train_dir.exists():
        train_images = list(images_train_dir.glob("*.jpg")) + list(images_train_dir.glob("*.jpeg")) + list(images_train_dir.glob("*.png"))
        all_images.extend(train_images)
    
    if images_val_dir.exists():
        val_images = list(images_val_dir.glob("*.jpg")) + list(images_val_dir.glob("*.jpeg")) + list(images_val_dir.glob("*.png"))
        all_images.extend(val_images)
    
    # Count labels
    labels_dir = dataset_path / "labels"
    labels_train_dir = labels_dir / "train"
    labels_val_dir = labels_dir / "val"
    
    all_labels = []
    root_labels = []
    train_labels = []
    val_labels = []
    
    if labels_dir.exists():
        root_labels = list(labels_dir.glob("*.txt"))
        all_labels.extend(root_labels)
    
    if labels_train_dir.exists():
        train_labels = list(labels_train_dir.glob("*.txt"))
        all_labels.extend(train_labels)
    
    if labels_val_dir.exists():
        val_labels = list(labels_val_dir.glob("*.txt"))
        all_labels.extend(val_labels)
    
    # Check for metadata files
    classes_file = dataset_path / "classes.txt"
    data_yaml = dataset_path / "data.yaml"
    
    print("\n📊 Dataset Structure Analysis:")
    print(f"  • Root images: {len(root_images)}")
    print(f"  • Train images: {len(train_images)}")
    print(f"  • Val images: {len(val_images)}")
    print(f"  • Total images: {len(all_images)}")
    print(f"  • Root labels: {len(root_labels)}")
    print(f"  • Train labels: {len(train_labels)}")
    print(f"  • Val labels: {len(val_labels)}")
    print(f"  • Total labels: {len(all_labels)}")
    print(f"  • classes.txt: {'✅ Found' if classes_file.exists() else '❌ Not found'}")
    print(f"  • data.yaml: {'✅ Found' if data_yaml.exists() else '❌ Not found'}")
    
    # Read class names if available
    classes = []
    if classes_file.exists():
        with open(classes_file, 'r') as f:
            classes = [line.strip() for line in f.readlines()]
        print(f"  • Classes: {', '.join(classes)}")
    
    return {
        "root_images": len(root_images),
        "train_images": len(train_images),
        "val_images": len(val_images),
        "total_images": len(all_images),
        "root_labels": len(root_labels),
        "train_labels": len(train_labels),
        "val_labels": len(val_labels),
        "total_labels": len(all_labels),
        "classes": classes
    }

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
    
    url = f"{API_URL}/datasets/{dataset_id}/import/status"
    
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
    params = {"with_labels": "true", "limit": 100}
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            result = response.json()
            images = result.get('images', [])
            total = result.get('total', 0)
            
            print(f"✅ Found {total} images in dataset")
            return images, total
        else:
            print(f"❌ Failed to get images: {response.status_code}")
            return [], 0
    except Exception as e:
        print(f"❌ Error getting images: {str(e)}")
        return [], 0

def analyze_imported_images(images):
    """Analyze imported images to check if train/val subdirectories were processed correctly."""
    if not images:
        print("No images to analyze")
        return
    
    # Count images with labels
    images_with_labels = [img for img in images if img.get('labels', [])]
    
    # Group images by directory (based on filename)
    root_images = []
    train_images = []
    val_images = []
    
    for img in images:
        filename = img.get('filename', '')
        if 'train/' in filename:
            train_images.append(img)
        elif 'val/' in filename:
            val_images.append(img)
        else:
            root_images.append(img)
    
    # Count labels in each directory
    root_labels = sum(len(img.get('labels', [])) for img in root_images)
    train_labels = sum(len(img.get('labels', [])) for img in train_images)
    val_labels = sum(len(img.get('labels', [])) for img in val_images)
    
    print("\n📊 Imported Images Analysis:")
    print(f"  • Total images: {len(images)}")
    print(f"  • Images with labels: {len(images_with_labels)}")
    print(f"  • Root directory images: {len(root_images)}")
    print(f"  • Train directory images: {len(train_images)}")
    print(f"  • Val directory images: {len(val_images)}")
    print(f"  • Root directory labels: {root_labels}")
    print(f"  • Train directory labels: {train_labels}")
    print(f"  • Val directory labels: {val_labels}")
    
    # Sample of images
    print("\nSample Images:")
    table_data = []
    
    for i, img in enumerate(images[:10]):
        filename = img.get('filename', 'unknown')
        label_count = len(img.get('labels', []))
        width = img.get('width', 0)
        height = img.get('height', 0)
        
        table_data.append([i+1, filename, f"{width}x{height}", label_count])
    
    headers = ["#", "Filename", "Dimensions", "Labels"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

def verify_fix():
    """Verify if the YOLO import service fix is working correctly."""
    print("\n" + "="*60)
    print("🔍 YOLO IMPORT SERVICE FIX VERIFICATION")
    print("="*60)
    
    # Analyze dataset structure
    structure = analyze_dataset_structure(DATASET_DIR)
    if not structure:
        return
    
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
        images, total = get_dataset_images(dataset_id)
        
        # Analyze imported images
        analyze_imported_images(images)
        
        # Verify results
        print("\n🔍 Verification Results:")
        print(f"  • Expected total images: {structure['total_images']}")
        print(f"  • Actual images processed: {total}")
        
        if total == structure['total_images']:
            print("✅ All images were processed correctly!")
        else:
            print("❌ Not all images were processed!")
        
        # Check if train/val subdirectories were processed
        train_images = [img for img in images if 'train/' in img.get('filename', '')]
        if structure['train_images'] > 0 and len(train_images) > 0:
            print("✅ Train subdirectory images were processed correctly!")
        elif structure['train_images'] > 0:
            print("❌ Train subdirectory images were not processed!")
        
        val_images = [img for img in images if 'val/' in img.get('filename', '')]
        if structure['val_images'] > 0 and len(val_images) > 0:
            print("✅ Val subdirectory images were processed correctly!")
        elif structure['val_images'] > 0:
            print("❌ Val subdirectory images were not processed!")
    
    # Clean up
    if os.path.exists(OUTPUT_ZIP):
        os.remove(OUTPUT_ZIP)
        print(f"Cleaned up {OUTPUT_ZIP}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    verify_fix()
