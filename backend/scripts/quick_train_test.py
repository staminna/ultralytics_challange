#!/usr/bin/env python3
"""
Quick YOLO Training Test - Minimal epochs to verify functionality
"""
import subprocess
from pathlib import Path

def quick_test():
    """Quick training test with minimal epochs."""
    backend_dir = Path(__file__).parent.parent
    datasets_dir = backend_dir / "datasets"
    
    print("🧪 Quick YOLO Training Test")
    print("Testing with minimal epochs to verify functionality\n")
    
    # Test COCO8 with 2 epochs
    print("Testing COCO8 (2 epochs)...")
    cmd = [
        "yolo", "detect", "train",
        f"data={datasets_dir}/raw/coco8.yaml",
        "model=yolo11n.pt",
        "epochs=2",
        "imgsz=640",
        "batch=2",
        "save=False",
        "plots=False",
        "patience=1",
        "exist_ok=True"
    ]
    
    try:
        result = subprocess.run(cmd, cwd=str(datasets_dir))
        if result.returncode == 0:
            print("✅ COCO8 quick test PASSED!")
        else:
            print("❌ COCO8 quick test FAILED")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    quick_test()
