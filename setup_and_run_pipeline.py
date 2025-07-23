#!/usr/bin/env python3
"""
Setup and Run Complete Pipeline

This script:
1. Downloads COCO datasets if missing
2. Runs the YOLO pipeline to generate labeled images
3. Shows results summary
"""
import os
import sys
import subprocess
from pathlib import Path

def setup_datasets():
    """Download COCO datasets if they don't exist."""
    backend_dir = Path(__file__).parent / "backend"
    datasets_dir = backend_dir / "datasets"
    
    # Check if datasets exist
    coco8_exists = (datasets_dir / "coco8").exists()
    coco128_exists = (datasets_dir / "coco128").exists()
    
    if coco8_exists and coco128_exists:
        print("✅ COCO datasets already exist")
        return True
    
    print("📥 Downloading COCO datasets...")
    
    # Run the download script
    download_script = backend_dir / "scripts" / "download_coco_to_backend.py"
    if not download_script.exists():
        print("❌ Download script not found")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(download_script)],
            cwd=str(backend_dir / "scripts"),
            timeout=300,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ COCO datasets downloaded successfully")
            return True
        else:
            print(f"❌ Download failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Download timed out")
        return False
    except Exception as e:
        print(f"❌ Download error: {e}")
        return False

def run_pipeline():
    """Run the YOLO pipeline."""
    backend_dir = Path(__file__).parent / "backend"
    pipeline_script = backend_dir / "run_pipeline.py"
    
    if not pipeline_script.exists():
        print("❌ Pipeline script not found")
        return False
    
    print("🚀 Running YOLO pipeline...")
    
    try:
        result = subprocess.run(
            [sys.executable, str(pipeline_script)],
            cwd=str(backend_dir),
            timeout=600
        )
        
        if result.returncode == 0:
            print("✅ Pipeline completed successfully")
            return True
        else:
            print("❌ Pipeline failed")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Pipeline timed out")
        return False
    except Exception as e:
        print(f"❌ Pipeline error: {e}")
        return False

def show_results():
    """Show pipeline results."""
    backend_dir = Path(__file__).parent / "backend"
    output_dir = backend_dir / "pipeline_output"
    
    if not output_dir.exists():
        print("❌ No pipeline output found")
        return
    
    print("\n📊 Pipeline Results:")
    print(f"📁 Output directory: {output_dir}")
    
    # Count results
    total_images = 0
    total_labeled = 0
    
    for dataset_dir in output_dir.iterdir():
        if dataset_dir.is_dir():
            labeled_images = list(dataset_dir.glob("labeled_*.jpg"))
            original_images = list(dataset_dir.glob("original_*.jpg"))
            
            total_labeled += len(labeled_images)
            total_images += len(original_images)
            
            print(f"  📂 {dataset_dir.name}: {len(original_images)} images, {len(labeled_images)} labeled")
    
    print(f"\n🎯 Total: {total_images} images processed, {total_labeled} labeled images created")
    
    # Show summary file if exists
    summary_file = output_dir / "pipeline_summary.json"
    if summary_file.exists():
        print(f"📋 Detailed summary: {summary_file}")

def main():
    """Main function."""
    print("🔧 YOLO Pipeline Setup and Execution")
    print("=" * 50)
    
    # Step 1: Setup datasets
    if not setup_datasets():
        print("❌ Failed to setup datasets")
        return 1
    
    # Step 2: Run pipeline
    if not run_pipeline():
        print("❌ Failed to run pipeline")
        return 1
    
    # Step 3: Show results
    show_results()
    
    print("\n✅ Complete pipeline execution finished!")
    print("🔍 Check backend/pipeline_output/ for labeled images")
    
    return 0

if __name__ == "__main__":
    exit(main())
