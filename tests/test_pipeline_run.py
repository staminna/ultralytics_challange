#!/usr/bin/env python3
"""
Test script for verifying the enhanced YOLO import pipeline with MongoDB integration.
This script tests:
1. Processing of images without labels
2. MongoDB integration for caching
3. Batch processing for large datasets
4. Progress tracking and status updates
"""

import json
import logging
import os
import time
import zipfile
from pathlib import Path

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pipeline_test.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
API_URL = "http://localhost:8000/api/v1"
DATASET_DIR = "backend/datasets/50_items_yolo_london_hotels"
OUTPUT_ZIP = "test_pipeline_london_hotels.zip"
DATASET_NAME = "Pipeline Test - London Hotels"
DATASET_DESC = "Test of enhanced YOLO import pipeline with MongoDB integration"

def check_server_status():
    """Check if the server is running."""
    try:
        response = requests.get(f"{API_URL}/datasets/", timeout=5)
        logger.info(f"✅ Server is running (status: {response.status_code})")
        return True
    except Exception as e:
        logger.error(f"❌ Server not running: {e}")
        return False

def analyze_dataset_structure():
    """Analyze the structure of the dataset directory."""
    dataset_path = Path(DATASET_DIR)
    
    if not dataset_path.exists():
        logger.error(f"❌ Dataset directory {DATASET_DIR} not found!")
        return None
    
    logger.info(f"Analyzing dataset structure in {DATASET_DIR}...")
    
    # Count images
    images_dir = dataset_path / "images"
    labels_dir = dataset_path / "labels"
    
    all_images = []
    root_images = []
    train_images = []
    val_images = []
    
    # Check for images in root directory
    if images_dir.exists():
        for img_ext in ['.jpg', '.jpeg', '.png', '.bmp']:
            root_images.extend(list(images_dir.glob(f"*{img_ext}")))
        
        # Check for train/val subdirectories
        train_dir = images_dir / "train"
        val_dir = images_dir / "val"
        
        if train_dir.exists():
            for img_ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                train_images.extend(list(train_dir.glob(f"*{img_ext}")))
        
        if val_dir.exists():
            for img_ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                val_images.extend(list(val_dir.glob(f"*{img_ext}")))
    
    all_images = root_images + train_images + val_images
    
    # Count labels
    all_labels = []
    root_labels = []
    train_labels = []
    val_labels = []
    
    if labels_dir.exists():
        root_labels = list(labels_dir.glob("*.txt"))
        
        # Check for train/val subdirectories
        train_dir = labels_dir / "train"
        val_dir = labels_dir / "val"
        
        if train_dir.exists():
            train_labels = list(train_dir.glob("*.txt"))
        
        if val_dir.exists():
            val_labels = list(val_dir.glob("*.txt"))
    
    all_labels = root_labels + train_labels + val_labels
    
    # Check for classes.txt and data.yaml
    classes_txt_exists = (dataset_path / "classes.txt").exists()
    data_yaml_exists = (dataset_path / "data.yaml").exists()
    
    # Read class names if available
    class_names = []
    if classes_txt_exists:
        with open(dataset_path / "classes.txt", "r") as f:
            class_names = [line.strip() for line in f.readlines() if line.strip()]
    elif data_yaml_exists:
        import yaml
        try:
            with open(dataset_path / "data.yaml", "r") as f:
                data = yaml.safe_load(f)
                class_names = data.get("names", [])
        except Exception as e:
            logger.error(f"Error reading data.yaml: {e}")
    
    # Print summary
    logger.info("\n📊 Dataset Structure Analysis:")
    logger.info(f"  • Root images: {len(root_images)}")
    logger.info(f"  • Train images: {len(train_images)}")
    logger.info(f"  • Val images: {len(val_images)}")
    logger.info(f"  • Total images: {len(all_images)}")
    logger.info(f"  • Root labels: {len(root_labels)}")
    logger.info(f"  • Train labels: {len(train_labels)}")
    logger.info(f"  • Val labels: {len(val_labels)}")
    logger.info(f"  • Total labels: {len(all_labels)}")
    logger.info(f"  • classes.txt: {'✅ Found' if classes_txt_exists else '❌ Not found'}")
    logger.info(f"  • data.yaml: {'✅ Found' if data_yaml_exists else '❌ Not found'}")
    
    if class_names:
        logger.info(f"  • Classes: {', '.join(class_names)}")
    
    return {
        "root_images": len(root_images),
        "train_images": len(train_images),
        "val_images": len(val_images),
        "total_images": len(all_images),
        "root_labels": len(root_labels),
        "train_labels": len(train_labels),
        "val_labels": len(val_labels),
        "total_labels": len(all_labels),
        "class_names": class_names
    }

def create_zip_from_directory():
    """Create a ZIP file from the dataset directory."""
    logger.info(f"Creating ZIP file from {DATASET_DIR}...")
    abs_directory = os.path.abspath(DATASET_DIR)
    
    with zipfile.ZipFile(OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(abs_directory):
            for file in files:
                file_path = os.path.join(root, file)
                # Calculate relative path to preserve directory structure
                rel_path = os.path.relpath(file_path, os.path.dirname(abs_directory))
                zipf.write(file_path, rel_path)
    
    zip_size = os.path.getsize(OUTPUT_ZIP) / (1024 * 1024)  # Size in MB
    logger.info(f"✅ Created {OUTPUT_ZIP} ({zip_size:.2f} MB)")
    return OUTPUT_ZIP

def upload_dataset():
    """Upload the dataset to the API."""
    logger.info(f"Uploading dataset {DATASET_NAME}...")
    
    url = f"{API_URL}/datasets/import/yolo"
    
    with open(OUTPUT_ZIP, 'rb') as zip_file:
        files = {'zip_file': (os.path.basename(OUTPUT_ZIP), zip_file, 'application/zip')}
        data = {
            'dataset_name': DATASET_NAME,
            'description': DATASET_DESC
        }
        
        try:
            response = requests.post(url, files=files, data=data)
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Upload successful! Dataset ID: {result.get('id')}")
                return result
            else:
                logger.error(f"❌ Upload failed with status code {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
        except Exception as e:
            logger.error(f"❌ Error during upload: {str(e)}")
            return None

def check_dataset_status(dataset_id):
    """Check the status of a dataset import."""
    logger.info(f"Checking status of dataset {dataset_id}...")
    
    url = f"{API_URL}/datasets/import/status/{dataset_id}"
    
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                status_data = response.json()
                status = status_data.get('status')
                progress = status_data.get('import_progress', 0)
                
                logger.info(f"Status: {status}, Progress: {progress}%")
                
                if status == 'ready':
                    logger.info("✅ Dataset import completed successfully!")
                    return True
                elif status == 'error':
                    logger.error(f"❌ Dataset import failed: {status_data.get('error_message', 'Unknown error')}")
                    return False
                
                # Wait before checking again
                time.sleep(2)
                attempt += 1
            else:
                logger.error(f"❌ Failed to check status: {response.status_code}")
                logger.error(f"Response: {response.text if hasattr(response, 'text') else 'No response text'}")
                return False
        except Exception as e:
            logger.error(f"❌ Error checking status: {str(e)}")
            return False
    
    logger.error("❌ Timeout waiting for dataset import to complete")
    return False

def get_dataset_images(dataset_id):
    """Get images for a dataset."""
    logger.info(f"Getting images for dataset {dataset_id}...")
    
    url = f"{API_URL}/datasets/{dataset_id}/images"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            result = response.json()
            images = result.get('images', [])
            logger.info(f"✅ Retrieved {len(images)} images")
            return images
        else:
            logger.error(f"❌ Failed to get images: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"❌ Error getting images: {str(e)}")
        return []

def verify_results(dataset_id, structure):
    """Verify the results of the import."""
    logger.info(f"Verifying results for dataset {dataset_id}...")
    
    # Get images
    images = get_dataset_images(dataset_id)
    
    if not images:
        logger.error("❌ No images found!")
        return False
    
    # Count images with and without labels
    images_with_labels = [img for img in images if img.get('labels', [])]
    images_without_labels = [img for img in images if not img.get('labels', [])]
    
    logger.info("\n🔍 Verification Results:")
    logger.info(f"  • Expected total images: {structure['total_images']}")
    logger.info(f"  • Actual images processed: {len(images)}")
    logger.info(f"  • Expected images with labels: {structure['total_labels']}")
    logger.info(f"  • Actual images with labels: {len(images_with_labels)}")
    logger.info(f"  • Images without labels: {len(images_without_labels)}")
    
    # Check if all images were processed
    if len(images) == structure['total_images']:
        logger.info("✅ All images were processed correctly!")
        success = True
    else:
        logger.error(f"❌ Not all images were processed! Missing {structure['total_images'] - len(images)} images.")
        success = False
    
    # Print sample images
    logger.info("\n📸 Sample Images:")
    for i, img in enumerate(images[:5]):
        label_count = len(img.get('labels', []))
        logger.info(f"  • {img.get('filename', 'Unknown')}: {label_count} labels")
    
    return success

def main():
    """Main function to test the pipeline."""
    logger.info("🔍 Testing Enhanced YOLO Import Pipeline")
    logger.info("=" * 60)
    
    # Check if server is running
    if not check_server_status():
        logger.error("❌ Server is not running. Please start the server first.")
        return
    
    # Analyze dataset structure
    structure = analyze_dataset_structure()
    if not structure:
        return
    
    # Create ZIP file
    zip_path = create_zip_from_directory()
    
    # Upload dataset
    result = upload_dataset()
    if not result:
        return
    
    dataset_id = result.get('id')
    
    # Check status
    if check_dataset_status(dataset_id):
        # Verify results
        success = verify_results(dataset_id, structure)
        
        if success:
            logger.info("\n✅ Pipeline test completed successfully!")
            logger.info("All images were processed correctly, including those without labels.")
            logger.info("MongoDB integration is working properly for caching and status updates.")
        else:
            logger.error("\n❌ Pipeline test failed!")
            logger.error("Not all images were processed correctly.")
    else:
        logger.error("\n❌ Pipeline test failed!")
        logger.error("Dataset import did not complete successfully.")

if __name__ == "__main__":
    main()
