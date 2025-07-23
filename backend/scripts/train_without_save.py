#!/usr/bin/env python3
"""
YOLO Training Script - Avoids pandas/numpy save issues

This script runs YOLO training with flags that prevent the pandas error
while still allowing full training functionality.
"""
import subprocess
import sys
from pathlib import Path

def train_yolo_safe(dataset, epochs=50, batch=8, imgsz=640):
    """Train YOLO model avoiding the pandas save error."""
    
    # Project paths
    backend_dir = Path(__file__).parent.parent
    datasets_dir = backend_dir / "datasets"
    yaml_file = datasets_dir / "raw" / f"{dataset}.yaml"
    
    if not yaml_file.exists():
        print(f"❌ Dataset YAML not found: {yaml_file}")
        return False
    
    print(f"🚀 Training {dataset} for {epochs} epochs...")
    print(f"📁 Dataset: {yaml_file}")
    
    # Training command that avoids the pandas error
    cmd = [
        "yolo", "detect", "train",
        f"data={yaml_file}",
        "model=yolo11n.pt",
        f"epochs={epochs}",
        f"imgsz={imgsz}",
        f"batch={batch}",
        "save=False",      # Prevents model saving that triggers pandas error
        "plots=False",     # Prevents plot generation that uses pandas
        "val=True",        # Still run validation
        "verbose=True",    # Keep detailed output
        "patience=10",     # Early stopping patience
        "exist_ok=True"    # Allow overwriting runs
    ]
    
    try:
        print(f"Running: {' '.join(cmd)}")
        
        # Run training
        result = subprocess.run(
            cmd,
            cwd=str(datasets_dir),
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ {dataset} training completed successfully!")
            return True
        else:
            print(f"❌ {dataset} training failed with exit code {result.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Error during training: {e}")
        return False

def main():
    print("YOLO Training Script - Safe Mode")
    print("Avoids pandas/numpy compatibility issues\n")
    
    if len(sys.argv) < 2:
        print("Usage: python train_without_save.py <dataset> [epochs] [batch_size]")
        print("Available datasets: coco8, coco128")
        print("Examples:")
        print("  python train_without_save.py coco8 10")
        print("  python train_without_save.py coco128 50 16")
        return 1
    
    dataset = sys.argv[1]
    epochs = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    batch = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    
    # Validate dataset
    if dataset not in ["coco8", "coco128"]:
        print(f"❌ Unknown dataset: {dataset}")
        print("Available datasets: coco8, coco128")
        return 1
    
    # Run training
    success = train_yolo_safe(dataset, epochs, batch)
    
    if success:
        print(f"\n🎉 Training completed successfully!")
        print(f"📊 Dataset: {dataset}")
        print(f"🔄 Epochs: {epochs}")
        print(f"📦 Batch size: {batch}")
        print("\n💡 Note: Model weights not saved due to pandas compatibility issue.")
        print("   Training metrics were displayed during the process.")
        return 0
    else:
        print(f"\n❌ Training failed. Check the error messages above.")
        return 1

if __name__ == "__main__":
    exit(main())
