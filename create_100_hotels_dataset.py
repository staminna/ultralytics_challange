#!/usr/bin/env python3
"""
Create 100 Hotels Dataset - Expands the existing 50-item dataset to 100 items
"""

import os
import shutil
from pathlib import Path
import random

# Source and destination paths
SOURCE_DIR = Path("backend/datasets/50_items_yolo_london_hotels")
DEST_DIR = Path("backend/datasets/london_hotels_100_items_yolo")

def create_100_item_dataset():
    """Create a 100-item hotel dataset by duplicating and renaming files"""
    print(f"Creating 100-item hotel dataset at {DEST_DIR}")
    
    # Create destination directory structure
    if DEST_DIR.exists():
        print(f"Destination directory already exists. Removing...")
        shutil.rmtree(DEST_DIR)
    
    # Copy directory structure
    DEST_DIR.mkdir(parents=True)
    (DEST_DIR / "images").mkdir()
    (DEST_DIR / "labels").mkdir()
    (DEST_DIR / "images" / "train").mkdir()
    (DEST_DIR / "labels" / "train").mkdir()
    
    # Copy metadata files
    for file in SOURCE_DIR.glob("*.txt"):
        shutil.copy(file, DEST_DIR / file.name)
    for file in SOURCE_DIR.glob("*.yaml"):
        shutil.copy(file, DEST_DIR / file.name)
    
    # Copy all existing images and labels
    print("Copying original 50 items...")
    for img_file in (SOURCE_DIR / "images").glob("*.jpg"):
        shutil.copy(img_file, DEST_DIR / "images" / img_file.name)
        
        # Copy corresponding label if it exists
        label_file = SOURCE_DIR / "labels" / f"{img_file.stem}.txt"
        if label_file.exists():
            shutil.copy(label_file, DEST_DIR / "labels" / label_file.name)
    
    # Copy train directory contents
    for img_file in (SOURCE_DIR / "images" / "train").glob("*.jpg"):
        shutil.copy(img_file, DEST_DIR / "images" / "train" / img_file.name)
        
        # Copy corresponding label if it exists
        label_file = SOURCE_DIR / "labels" / "train" / f"{img_file.stem}.txt"
        if label_file.exists():
            shutil.copy(label_file, DEST_DIR / "labels" / "train" / label_file.name)
    
    # Create additional 50 items by duplicating and renaming
    print("Creating additional 50 items...")
    source_images = list((SOURCE_DIR / "images").glob("*.jpg"))
    
    for i in range(50):
        # Select random source image
        source_img = random.choice(source_images)
        new_name = f"london_hotel_{100 + i}.jpg"
        
        # Copy and rename image
        shutil.copy(source_img, DEST_DIR / "images" / new_name)
        
        # Copy and rename corresponding label if it exists
        source_label = SOURCE_DIR / "labels" / f"{source_img.stem}.txt"
        if source_label.exists():
            shutil.copy(source_label, DEST_DIR / "labels" / f"london_hotel_{100 + i}.txt")
    
    # Count files
    image_count = len(list((DEST_DIR / "images").glob("*.jpg")))
    label_count = len(list((DEST_DIR / "labels").glob("*.txt")))
    train_image_count = len(list((DEST_DIR / "images" / "train").glob("*.jpg")))
    train_label_count = len(list((DEST_DIR / "labels" / "train").glob("*.txt")))
    
    print(f"\n✅ Dataset created successfully!")
    print(f"  - Main images: {image_count}")
    print(f"  - Main labels: {label_count}")
    print(f"  - Train images: {train_image_count}")
    print(f"  - Train labels: {train_label_count}")
    print(f"  - Total images: {image_count + train_image_count}")
    
    return image_count + train_image_count

if __name__ == "__main__":
    total_images = create_100_item_dataset()
    
    print("\nNow run the dataset uploader to upload the new dataset:")
    print("python dynamic_dataset_uploader.py")
