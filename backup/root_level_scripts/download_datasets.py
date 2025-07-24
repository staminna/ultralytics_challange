#!/usr/bin/env python3
"""
YOLO CLI Dataset Downloader

Uses the YOLO CLI tool to download datasets directly into backend/datasets folder.
Supports all official YOLO datasets and creates proper directory structure.
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path
import yaml

class YOLODatasetDownloader:
    def __init__(self):
        self.backend_dir = Path(__file__).parent / "backend"
        self.datasets_dir = self.backend_dir / "datasets"
        self.raw_dir = self.datasets_dir / "raw"
        
        # Create directories
        self.datasets_dir.mkdir(exist_ok=True)
        self.raw_dir.mkdir(exist_ok=True)
        
        # Available datasets
        self.available_datasets = {
            "coco8": {
                "description": "COCO 8 images sample dataset",
                "size": "~6MB",
                "images": 8
            },
            "coco128": {
                "description": "COCO 128 images sample dataset", 
                "size": "~13MB",
                "images": 128
            },
            "coco": {
                "description": "Full COCO dataset",
                "size": "~20GB",
                "images": 118000
            },
            "VOC": {
                "description": "Pascal VOC dataset",
                "size": "~2GB", 
                "images": 16551
            },
            "Open Images v7": {
                "description": "Open Images v7 dataset",
                "size": "~500GB",
                "images": 1700000
            }
        }
    
    def check_yolo_cli(self):
        """Check if YOLO CLI is available."""
        try:
            result = subprocess.run(
                ["yolo", "version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"✅ YOLO CLI found: {version}")
                return True
            else:
                print("❌ YOLO CLI not working properly")
                return False
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ YOLO CLI not found. Install with: pip install ultralytics")
            return False
    
    def download_dataset(self, dataset_name, force=False):
        """Download a dataset using YOLO CLI."""
        if dataset_name not in self.available_datasets:
            print(f"❌ Unknown dataset: {dataset_name}")
            print(f"Available datasets: {list(self.available_datasets.keys())}")
            return False
        
        dataset_info = self.available_datasets[dataset_name]
        print(f"\n📥 Downloading {dataset_name}")
        print(f"   Description: {dataset_info['description']}")
        print(f"   Size: {dataset_info['size']}")
        print(f"   Images: {dataset_info['images']}")
        
        # Check if already exists
        dataset_path = self.datasets_dir / dataset_name
        if dataset_path.exists() and not force:
            print(f"✅ Dataset {dataset_name} already exists (use --force to re-download)")
            return True
        
        try:
            # Use YOLO CLI to download dataset
            cmd = [
                "yolo", "detect", "val",
                f"data={dataset_name}",  # Use dataset name directly
                "model=yolo11n.pt",
                "epochs=0",
                "save=False",
                "plots=False"
            ]
            
            print(f"🔄 Running: {' '.join(cmd)}")
            
            # Set environment to download to our directory
            env = os.environ.copy()
            env["YOLO_DATASETS_DIR"] = str(self.datasets_dir.absolute())
            
            result = subprocess.run(
                cmd,
                cwd=str(self.datasets_dir),
                env=env,
                timeout=1800,  # 30 minutes timeout
                text=True
            )
            
            if result.returncode == 0:
                print(f"✅ Dataset {dataset_name} downloaded successfully")
                self.update_yaml_config(dataset_name)
                return True
            else:
                print(f"❌ Download failed for {dataset_name}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"❌ Download timed out for {dataset_name}")
            return False
        except Exception as e:
            print(f"❌ Error downloading {dataset_name}: {e}")
            return False
    
    def update_yaml_config(self, dataset_name):
        """Update YAML config with correct paths after download."""
        dataset_path = self.datasets_dir / dataset_name
        yaml_path = self.raw_dir / f"{dataset_name}.yaml"
        
        if not dataset_path.exists():
            return
        
        # Find actual image directories
        images_dir = dataset_path / "images"
        train_dir = None
        val_dir = None
        
        if images_dir.exists():
            for subdir in images_dir.iterdir():
                if subdir.is_dir():
                    if "train" in subdir.name:
                        train_dir = f"images/{subdir.name}"
                    elif "val" in subdir.name:
                        val_dir = f"images/{subdir.name}"
        
        # Update YAML
        yaml_config = {
            "path": str(dataset_path.absolute()),
            "train": train_dir or "images/train",
            "val": val_dir or "images/val", 
            "names": self.get_class_names(dataset_name)
        }
        
        with open(yaml_path, 'w') as f:
            yaml.dump(yaml_config, f, default_flow_style=False)
        
        print(f"📝 Updated config: {yaml_path}")
    
    def get_class_names(self, dataset_name):
        """Get class names for dataset."""
        if dataset_name.startswith("coco"):
            return {
                0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle', 4: 'airplane', 5: 'bus',
                6: 'train', 7: 'truck', 8: 'boat', 9: 'traffic light', 10: 'fire hydrant',
                11: 'stop sign', 12: 'parking meter', 13: 'bench', 14: 'bird', 15: 'cat',
                16: 'dog', 17: 'horse', 18: 'sheep', 19: 'cow', 20: 'elephant', 21: 'bear',
                22: 'zebra', 23: 'giraffe', 24: 'backpack', 25: 'umbrella', 26: 'handbag',
                27: 'tie', 28: 'suitcase', 29: 'frisbee', 30: 'skis', 31: 'snowboard',
                32: 'sports ball', 33: 'kite', 34: 'baseball bat', 35: 'baseball glove',
                36: 'skateboard', 37: 'surfboard', 38: 'tennis racket', 39: 'bottle',
                40: 'wine glass', 41: 'cup', 42: 'fork', 43: 'knife', 44: 'spoon', 45: 'bowl',
                46: 'banana', 47: 'apple', 48: 'sandwich', 49: 'orange', 50: 'broccoli',
                51: 'carrot', 52: 'hot dog', 53: 'pizza', 54: 'donut', 55: 'cake', 56: 'chair',
                57: 'couch', 58: 'potted plant', 59: 'bed', 60: 'dining table', 61: 'toilet',
                62: 'tv', 63: 'laptop', 64: 'mouse', 65: 'remote', 66: 'keyboard',
                67: 'cell phone', 68: 'microwave', 69: 'oven', 70: 'toaster', 71: 'sink',
                72: 'refrigerator', 73: 'book', 74: 'clock', 75: 'vase', 76: 'scissors',
                77: 'teddy bear', 78: 'hair drier', 79: 'toothbrush'
            }
        else:
            return {}  # Will be filled by YOLO
    
    def list_datasets(self):
        """List available datasets."""
        print("\n📋 Available Datasets:")
        for name, info in self.available_datasets.items():
            status = "✅ Downloaded" if (self.datasets_dir / name).exists() else "⬇️  Available"
            print(f"  {name}: {info['description']} ({info['size']}) - {status}")
    
    def show_downloaded(self):
        """Show downloaded datasets."""
        print("\n📁 Downloaded Datasets:")
        
        if not self.datasets_dir.exists():
            print("  No datasets directory found")
            return
        
        found_any = False
        for item in self.datasets_dir.iterdir():
            if item.is_dir() and item.name != "raw":
                found_any = True
                
                # Count images
                images_count = 0
                images_dir = item / "images"
                if images_dir.exists():
                    for subdir in images_dir.rglob("*"):
                        if subdir.is_file() and subdir.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                            images_count += 1
                
                # Check for labels
                labels_dir = item / "labels"
                labels_count = 0
                if labels_dir.exists():
                    labels_count = len(list(labels_dir.rglob("*.txt")))
                
                print(f"  📂 {item.name}: {images_count} images, {labels_count} labels")
        
        if not found_any:
            print("  No datasets downloaded yet")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="YOLO Dataset Downloader")
    parser.add_argument("action", choices=["list", "download", "status"], 
                       help="Action to perform")
    parser.add_argument("dataset", nargs="?", 
                       help="Dataset name to download")
    parser.add_argument("--force", action="store_true",
                       help="Force re-download if dataset exists")
    
    args = parser.parse_args()
    
    downloader = YOLODatasetDownloader()
    
    print("🚀 YOLO Dataset Downloader")
    print("=" * 40)
    
    # Check YOLO CLI
    if not downloader.check_yolo_cli():
        return 1
    
    if args.action == "list":
        downloader.list_datasets()
    elif args.action == "status":
        downloader.show_downloaded()
    elif args.action == "download":
        if not args.dataset:
            print("❌ Please specify a dataset name")
            downloader.list_datasets()
            return 1
        
        success = downloader.download_dataset(args.dataset, args.force)
        if success:
            print(f"\n✅ Dataset {args.dataset} ready for use!")
            print(f"📁 Location: {downloader.datasets_dir / args.dataset}")
            print(f"📝 Config: {downloader.raw_dir / args.dataset}.yaml")
        else:
            return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
