#!/usr/bin/env python3
"""
Script to create a large YOLO dataset with 1000 images.
This script will:
1. Download images from a public dataset
2. Create proper YOLO directory structure
3. Generate metadata files (classes.txt, data.yaml)
4. Create sample labels for some images
"""

import os
import random
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
import yaml
from tqdm import tqdm

# Configuration
OUTPUT_DIR = "backend/datasets/large_yolo_dataset_1000"
IMAGES_DIR = f"{OUTPUT_DIR}/images"
LABELS_DIR = f"{OUTPUT_DIR}/labels"
NUM_IMAGES = 1000
NUM_LABELED_IMAGES = 200  # 20% of images will have labels
IMAGE_SIZE = (640, 480)  # Target size for downloaded images

# Unsplash API for random images (no API key needed for this demo endpoint)
UNSPLASH_URL = "https://source.unsplash.com/random"

# COCO class names (subset)
CLASS_NAMES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", 
    "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", 
    "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", 
    "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee"
]

def setup_directories():
    """Create the necessary directory structure."""
    print(f"Setting up directory structure in {OUTPUT_DIR}...")
    
    # Create main directories
    os.makedirs(IMAGES_DIR, exist_ok=True)
    os.makedirs(LABELS_DIR, exist_ok=True)
    
    # Create train/val split directories
    os.makedirs(f"{IMAGES_DIR}/train", exist_ok=True)
    os.makedirs(f"{IMAGES_DIR}/val", exist_ok=True)
    os.makedirs(f"{LABELS_DIR}/train", exist_ok=True)
    os.makedirs(f"{LABELS_DIR}/val", exist_ok=True)
    
    print("✅ Directory structure created")

def download_image(index):
    """Download a random image from Unsplash."""
    try:
        # Determine if this image will be in train or val set (80/20 split)
        is_train = random.random() < 0.8
        subset = "train" if is_train else "val"
        
        # Define file paths
        img_filename = f"{subset}_{index:04d}.jpg"
        img_path = f"{IMAGES_DIR}/{subset}/{img_filename}"
        
        # Add random parameters to avoid caching
        params = {"random": random.randint(1, 10000000), "w": IMAGE_SIZE[0], "h": IMAGE_SIZE[1]}
        response = requests.get(f"{UNSPLASH_URL}/{IMAGE_SIZE[0]}x{IMAGE_SIZE[1]}", 
                               params=params, stream=True, timeout=10)
        
        if response.status_code == 200:
            with open(img_path, 'wb') as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)
            
            # Randomly decide if this image should have a label
            should_have_label = random.random() < (NUM_LABELED_IMAGES / NUM_IMAGES)
            
            if should_have_label:
                create_label_file(img_filename, subset)
                
            return True
        else:
            print(f"Failed to download image {index}: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"Error downloading image {index}: {str(e)}")
        return False

def create_label_file(img_filename, subset):
    """Create a YOLO format label file with random annotations."""
    # Extract base filename without extension
    base_filename = os.path.splitext(img_filename)[0]
    label_path = f"{LABELS_DIR}/{subset}/{base_filename}.txt"
    
    # Generate 1-3 random objects per image
    num_objects = random.randint(1, 3)
    
    with open(label_path, 'w') as f:
        for _ in range(num_objects):
            # Random class
            class_id = random.randint(0, len(CLASS_NAMES) - 1)
            
            # Random bounding box (x_center, y_center, width, height) - normalized 0-1
            x_center = random.uniform(0.2, 0.8)
            y_center = random.uniform(0.2, 0.8)
            width = random.uniform(0.1, 0.4)
            height = random.uniform(0.1, 0.4)
            
            # Ensure box stays within image bounds
            if x_center + width/2 > 1.0:
                width = (1.0 - x_center) * 2
            if y_center + height/2 > 1.0:
                height = (1.0 - y_center) * 2
                
            # Write YOLO format line: class_id x_center y_center width height
            f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")

def create_metadata_files():
    """Create classes.txt and data.yaml files."""
    print("Creating metadata files...")
    
    # Create classes.txt
    with open(f"{OUTPUT_DIR}/classes.txt", 'w') as f:
        for class_name in CLASS_NAMES:
            f.write(f"{class_name}\n")
    
    # Create data.yaml
    data_yaml = {
        'path': OUTPUT_DIR,
        'train': f"{IMAGES_DIR}/train",
        'val': f"{IMAGES_DIR}/val",
        'nc': len(CLASS_NAMES),  # number of classes
        'names': CLASS_NAMES
    }
    
    with open(f"{OUTPUT_DIR}/data.yaml", 'w') as f:
        yaml.dump(data_yaml, f, sort_keys=False)
    
    print("✅ Metadata files created")

def main():
    """Main function to create the dataset."""
    print(f"🔄 Creating large YOLO dataset with {NUM_IMAGES} images ({NUM_LABELED_IMAGES} labeled)")
    print("=" * 60)
    
    # Setup directory structure
    setup_directories()
    
    # Download images with progress bar
    print(f"Downloading {NUM_IMAGES} images (this may take a while)...")
    
    success_count = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(download_image, i) for i in range(NUM_IMAGES)]
        for future in tqdm(futures, total=NUM_IMAGES, desc="Downloading"):
            if future.result():
                success_count += 1
    
    # Create metadata files
    create_metadata_files()
    
    # Count actual files
    train_images = len(list(Path(f"{IMAGES_DIR}/train").glob("*.jpg")))
    val_images = len(list(Path(f"{IMAGES_DIR}/val").glob("*.jpg")))
    train_labels = len(list(Path(f"{LABELS_DIR}/train").glob("*.txt")))
    val_labels = len(list(Path(f"{LABELS_DIR}/val").glob("*.txt")))
    
    print("\n📊 Dataset Summary:")
    print(f"  • Total images: {train_images + val_images}/{NUM_IMAGES}")
    print(f"  • Training images: {train_images}")
    print(f"  • Validation images: {val_images}")
    print(f"  • Total labels: {train_labels + val_labels}/{NUM_LABELED_IMAGES}")
    print(f"  • Training labels: {train_labels}")
    print(f"  • Validation labels: {val_labels}")
    print(f"  • Classes: {len(CLASS_NAMES)}")
    
    print(f"\n✅ Dataset created at {os.path.abspath(OUTPUT_DIR)}")
    print("You can now use this dataset with the YOLO import service.")

if __name__ == "__main__":
    main()
