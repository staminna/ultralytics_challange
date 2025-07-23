#!/usr/bin/env python3
"""
COCO Dataset Downloader for Backend

This script uses YOLO CLI to download datasets directly to backend/datasets folder.
"""
import subprocess
import sys
import os
import shutil
from pathlib import Path

# Project paths
BACKEND_DIR = Path(__file__).parent.parent
DATASETS_DIR = BACKEND_DIR / "datasets"
RAW_DIR = DATASETS_DIR / "raw"

def setup_directories():
    """Create necessary directory structure."""
    DATASETS_DIR.mkdir(exist_ok=True)
    RAW_DIR.mkdir(exist_ok=True)
    print(f"✅ Created directory structure in {DATASETS_DIR}")

def download_with_yolo(dataset_name, target_dir):
    """Download dataset using YOLO CLI and move to target directory."""
    print(f"\n===== Downloading {dataset_name} =====")
    
    try:
        # Set environment variable to control where YOLO downloads datasets
        env = os.environ.copy()
        env['YOLO_DATASETS_DIR'] = str(target_dir.parent)
        
        # Use yolo val command to trigger dataset download
        cmd = ["yolo", "val", f"data={dataset_name}.yaml", "model=yolo11n.pt", "epochs=0"]
        print(f"Running: {' '.join(cmd)}")
        print(f"Target directory: {target_dir}")
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=600,  # 10 minutes timeout
            env=env,
            cwd=str(DATASETS_DIR)
        )
        
        if result.returncode == 0:
            print(f"✅ {dataset_name} downloaded successfully!")
            
            # Check if dataset was downloaded to default location and move it
            default_path = Path.home() / "2026" / "Ultralytics" / "datasets" / dataset_name
            if default_path.exists() and not target_dir.exists():
                print(f"Moving dataset from {default_path} to {target_dir}")
                shutil.move(str(default_path), str(target_dir))
            
            return True
        else:
            print(f"❌ {dataset_name} download failed")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ {dataset_name} download timed out")
        return False
    except Exception as e:
        print(f"❌ Error downloading {dataset_name}: {e}")
        return False

def create_yaml_configs():
    """Create YAML configuration files in the raw directory."""
    
    # COCO8 YAML
    coco8_yaml = RAW_DIR / "coco8.yaml"
    coco8_content = f"""# COCO8 dataset (first 8 images from COCO train2017) by Ultralytics
# Example usage: yolo train data=coco8.yaml
# parent
# ├── ultralytics
# └── datasets
#     └── coco8  ← downloads here (1 MB)

# Train/val/test sets as 1) dir: path/to/imgs, 2) file: path/to/imgs.txt, or 3) list: [path/to/imgs1, path/to/imgs2, ..]
path: {DATASETS_DIR / 'coco8'}  # dataset root dir
train: images/train  # train images (relative to 'path') 4 images
val: images/val  # val images (relative to 'path') 4 images
test:  # test images (optional)

# Classes
names:
  0: person
  1: bicycle
  2: car
  3: motorcycle
  4: airplane
  5: bus
  6: train
  7: truck
  8: boat
  9: traffic light
  10: fire hydrant
  11: stop sign
  12: parking meter
  13: bench
  14: bird
  15: cat
  16: dog
  17: horse
  18: sheep
  19: cow
  20: elephant
  21: bear
  22: zebra
  23: giraffe
  24: backpack
  25: umbrella
  26: handbag
  27: tie
  28: suitcase
  29: frisbee
  30: skis
  31: snowboard
  32: sports ball
  33: kite
  34: baseball bat
  35: baseball glove
  36: skateboard
  37: surfboard
  38: tennis racket
  39: bottle
  40: wine glass
  41: cup
  42: fork
  43: knife
  44: spoon
  45: bowl
  46: banana
  47: apple
  48: sandwich
  49: orange
  50: broccoli
  51: carrot
  52: hot dog
  53: pizza
  54: donut
  55: cake
  56: chair
  57: couch
  58: potted plant
  59: bed
  60: dining table
  61: toilet
  62: tv
  63: laptop
  64: mouse
  65: remote
  66: keyboard
  67: cell phone
  68: microwave
  69: oven
  70: toaster
  71: sink
  72: refrigerator
  73: book
  74: clock
  75: vase
  76: scissors
  77: teddy bear
  78: hair drier
  79: toothbrush
"""
    
    with open(coco8_yaml, 'w') as f:
        f.write(coco8_content)
    
    # COCO128 YAML
    coco128_yaml = RAW_DIR / "coco128.yaml"
    coco128_content = f"""# COCO128 dataset (first 128 images from COCO train2017) by Ultralytics
# Example usage: yolo train data=coco128.yaml

# Train/val/test sets as 1) dir: path/to/imgs, 2) file: path/to/imgs.txt, or 3) list: [path/to/imgs1, path/to/imgs2, ..]
path: {DATASETS_DIR / 'coco128'}  # dataset root dir
train: images/train2017  # train images (relative to 'path') 128 images
val: images/train2017  # val images (relative to 'path') 128 images
test:  # test images (optional)

# Classes (same as COCO8)
names:
  0: person
  1: bicycle
  2: car
  3: motorcycle
  4: airplane
  5: bus
  6: train
  7: truck
  8: boat
  9: traffic light
  10: fire hydrant
  11: stop sign
  12: parking meter
  13: bench
  14: bird
  15: cat
  16: dog
  17: horse
  18: sheep
  19: cow
  20: elephant
  21: bear
  22: zebra
  23: giraffe
  24: backpack
  25: umbrella
  26: handbag
  27: tie
  28: suitcase
  29: frisbee
  30: skis
  31: snowboard
  32: sports ball
  33: kite
  34: baseball bat
  35: baseball glove
  36: skateboard
  37: surfboard
  38: tennis racket
  39: bottle
  40: wine glass
  41: cup
  42: fork
  43: knife
  44: spoon
  45: bowl
  46: banana
  47: apple
  48: sandwich
  49: orange
  50: broccoli
  51: carrot
  52: hot dog
  53: pizza
  54: donut
  55: cake
  56: chair
  57: couch
  58: potted plant
  59: bed
  60: dining table
  61: toilet
  62: tv
  63: laptop
  64: mouse
  65: remote
  66: keyboard
  67: cell phone
  68: microwave
  69: oven
  70: toaster
  71: sink
  72: refrigerator
  73: book
  74: clock
  75: vase
  76: scissors
  77: teddy bear
  78: hair drier
  79: toothbrush
"""
    
    with open(coco128_yaml, 'w') as f:
        f.write(coco128_content)
    
    print(f"✅ Created YAML configs in {RAW_DIR}")
    return coco8_yaml, coco128_yaml

def check_dataset_structure():
    """Check and display the downloaded dataset structure."""
    print(f"\n===== Dataset Structure =====")
    
    for dataset_dir in DATASETS_DIR.iterdir():
        if dataset_dir.is_dir() and dataset_dir.name not in ['raw']:
            print(f"\n📁 {dataset_dir.name}/")
            
            # Count images
            image_count = 0
            for img_dir in dataset_dir.rglob("images"):
                if img_dir.is_dir():
                    jpg_count = len(list(img_dir.glob("**/*.jpg")))
                    png_count = len(list(img_dir.glob("**/*.png")))
                    image_count += jpg_count + png_count
                    print(f"  📷 images: {jpg_count + png_count} files")
            
            # Count labels
            label_count = 0
            for label_dir in dataset_dir.rglob("labels"):
                if label_dir.is_dir():
                    txt_count = len(list(label_dir.glob("**/*.txt")))
                    label_count += txt_count
                    print(f"  🏷️  labels: {txt_count} files")
            
            print(f"  📊 Total: {image_count} images, {label_count} labels")

def main():
    print("COCO Dataset Downloader for Backend")
    print(f"Target directory: {DATASETS_DIR}")
    
    # Check if yolo is installed
    try:
        result = subprocess.run(["yolo", "version"], check=True, capture_output=True, text=True)
        print(f"✅ YOLO CLI found: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ YOLO CLI not found. Install with: pip install ultralytics")
        return 1
    
    # Setup directories
    setup_directories()
    
    # Create YAML configs
    coco8_yaml, coco128_yaml = create_yaml_configs()
    
    # Download datasets
    datasets = [
        ("coco8", DATASETS_DIR / "coco8"),
        ("coco128", DATASETS_DIR / "coco128")
    ]
    
    success_count = 0
    for dataset_name, target_dir in datasets:
        if download_with_yolo(dataset_name, target_dir):
            success_count += 1
    
    print(f"\n===== Summary =====")
    print(f"Successfully downloaded: {success_count}/{len(datasets)} datasets")
    
    # Check structure
    check_dataset_structure()
    
    if success_count > 0:
        print(f"\n✅ Datasets are ready in {DATASETS_DIR}")
        print("You can now use these datasets with your backend services!")
    
    return 0 if success_count > 0 else 1

if __name__ == "__main__":
    exit(main())
