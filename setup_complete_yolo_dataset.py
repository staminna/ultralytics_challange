#!/usr/bin/env python3
"""
Set up a complete YOLO dataset with all London hotel images.
This combines the 10 labeled images + 46 additional images.
"""

import os
import shutil
from pathlib import Path
import zipfile

# Paths
DATASET_DIR = Path("backend/datasets/london_hotels_50_items_yolo")
ORIGINAL_YOLO = Path("backend/datasets/london_hotels_yolo")
ADDITIONAL_IMAGES = Path("backend/datasets/sample_images/london_hotels")

def setup_directory_structure():
    """Set up the proper YOLO directory structure."""
    print("🏗️  Setting up YOLO directory structure...")
    
    # Create main directories
    (DATASET_DIR / "images" / "train").mkdir(parents=True, exist_ok=True)
    (DATASET_DIR / "labels" / "train").mkdir(parents=True, exist_ok=True)
    
    # Remove the typo directory
    typo_dir = DATASET_DIR / "lables"
    if typo_dir.exists():
        shutil.rmtree(typo_dir)
        print("  ✅ Removed typo directory 'lables'")
    
    print("  ✅ Directory structure created")

def copy_original_yolo_data():
    """Copy the original 10 YOLO images and labels."""
    print("📋 Copying original YOLO data (10 images with labels)...")
    
    # Copy images
    src_images = ORIGINAL_YOLO / "images" / "train"
    dst_images = DATASET_DIR / "images" / "train"
    
    if src_images.exists():
        for img_file in src_images.glob("*.jpg"):
            shutil.copy2(img_file, dst_images)
            print(f"  📷 Copied {img_file.name}")
    
    # Copy labels
    src_labels = ORIGINAL_YOLO / "labels" / "train"
    dst_labels = DATASET_DIR / "labels" / "train"
    
    if src_labels.exists():
        for label_file in src_labels.glob("*.txt"):
            shutil.copy2(label_file, dst_labels)
            print(f"  🏷️  Copied {label_file.name}")

def copy_additional_images():
    """Copy the additional 46 images (without labels)."""
    print("📸 Copying additional images (46 images without labels)...")
    
    dst_images = DATASET_DIR / "images" / "train"
    
    if ADDITIONAL_IMAGES.exists():
        for img_file in ADDITIONAL_IMAGES.glob("*.jpg"):
            # Skip if already exists (from original YOLO dataset)
            if not (dst_images / img_file.name).exists():
                shutil.copy2(img_file, dst_images)
                print(f"  📷 Copied {img_file.name}")

def create_empty_label_files():
    """Create empty label files for images without labels."""
    print("🏷️  Creating empty label files for unlabeled images...")
    
    images_dir = DATASET_DIR / "images" / "train"
    labels_dir = DATASET_DIR / "labels" / "train"
    
    created_count = 0
    for img_file in images_dir.glob("*.jpg"):
        label_file = labels_dir / f"{img_file.stem}.txt"
        if not label_file.exists():
            # Create empty label file
            label_file.touch()
            created_count += 1
            print(f"  📝 Created empty label: {label_file.name}")
    
    print(f"  ✅ Created {created_count} empty label files")

def create_data_yaml():
    """Create the data.yaml file."""
    print("📄 Creating data.yaml file...")
    
    data_yaml_content = f"""# London Hotels Complete Dataset
path: {DATASET_DIR.absolute()}
train: images/train
val: images/train

# Classes (12 object types from COCO)
nc: 12
names: ['backpack', 'bed', 'bench', 'boat', 'book', 'chair', 'couch', 'dining table', 'person', 'tv', 'umbrella', 'wine glass']

# Dataset info
description: "Complete London Hotels dataset with 56 images (10 with YOLO labels, 46 ready for annotation)"
version: "1.0"
author: "Dataset Annotation Backend"
"""
    
    data_yaml_path = DATASET_DIR / "data.yaml"
    with open(data_yaml_path, 'w') as f:
        f.write(data_yaml_content)
    
    print(f"  ✅ Created data.yaml")

def create_classes_txt():
    """Create classes.txt file."""
    print("📋 Creating classes.txt file...")
    
    classes = [
        'backpack', 'bed', 'bench', 'boat', 'book', 'chair', 
        'couch', 'dining table', 'person', 'tv', 'umbrella', 'wine glass'
    ]
    
    classes_path = DATASET_DIR / "classes.txt"
    with open(classes_path, 'w') as f:
        for class_name in classes:
            f.write(f"{class_name}\n")
    
    print(f"  ✅ Created classes.txt with {len(classes)} classes")

def create_dataset_zip():
    """Create a ZIP file of the complete dataset."""
    print("📦 Creating dataset ZIP file...")
    
    zip_path = DATASET_DIR.parent / "london_hotels_complete_yolo.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(DATASET_DIR):
            for file in files:
                file_path = Path(root) / file
                # Get relative path from dataset directory
                arc_path = file_path.relative_to(DATASET_DIR)
                zipf.write(file_path, arc_path)
                print(f"  📁 Added to ZIP: {arc_path}")
    
    print(f"  ✅ Created ZIP: {zip_path}")
    return zip_path

def print_dataset_summary():
    """Print a summary of the created dataset."""
    print("\n📊 Dataset Summary")
    print("=" * 50)
    
    images_dir = DATASET_DIR / "images" / "train"
    labels_dir = DATASET_DIR / "labels" / "train"
    
    image_count = len(list(images_dir.glob("*.jpg")))
    label_count = len(list(labels_dir.glob("*.txt")))
    
    # Count non-empty labels
    labeled_count = 0
    for label_file in labels_dir.glob("*.txt"):
        if label_file.stat().st_size > 0:
            labeled_count += 1
    
    print(f"📷 Total Images: {image_count}")
    print(f"🏷️  Total Labels: {label_count}")
    print(f"✅ Images with annotations: {labeled_count}")
    print(f"📝 Images ready for annotation: {image_count - labeled_count}")
    print(f"📁 Dataset location: {DATASET_DIR}")
    print(f"📄 Data config: {DATASET_DIR / 'data.yaml'}")

def main():
    """Set up the complete YOLO dataset."""
    print("🚀 Setting up Complete London Hotels YOLO Dataset")
    print("=" * 60)
    
    # Step 1: Set up directory structure
    setup_directory_structure()
    
    # Step 2: Copy original YOLO data (10 images with labels)
    copy_original_yolo_data()
    
    # Step 3: Copy additional images (46 images)
    copy_additional_images()
    
    # Step 4: Create empty label files for unlabeled images
    create_empty_label_files()
    
    # Step 5: Create data.yaml
    create_data_yaml()
    
    # Step 6: Create classes.txt
    create_classes_txt()
    
    # Step 7: Create ZIP file
    zip_path = create_dataset_zip()
    
    # Step 8: Print summary
    print_dataset_summary()
    
    print(f"\n🎉 Complete YOLO dataset created successfully!")
    print(f"📦 ZIP file: {zip_path}")
    print(f"🔗 Ready to upload via: python upload_london_hotels.py")

if __name__ == "__main__":
    main()
