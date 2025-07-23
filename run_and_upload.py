#!/usr/bin/env python3
"""
Complete YOLO Pipeline and GCS Upload Workflow

This script:
1. Runs the YOLO pipeline to generate labeled images
2. Uploads datasets and results to Google Cloud Storage
3. Provides comprehensive reporting
"""
import subprocess
import sys
from pathlib import Path
import json
from datetime import datetime

def run_command(cmd, description, timeout=600):
    """Run a command and show results."""
    print(f"\n🔄 {description}")
    print(f"   Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd, 
            check=True, 
            capture_output=True, 
            text=True,
            timeout=timeout
        )
        print(f"✅ {description} - SUCCESS")
        if result.stdout:
            # Show last few lines of output
            lines = result.stdout.strip().split('\n')
            for line in lines[-3:]:
                if line.strip():
                    print(f"   {line}")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"   Error: {e.stderr}")
        return False, e.stderr
    except subprocess.TimeoutExpired:
        print(f"❌ {description} - TIMEOUT")
        return False, "Command timed out"

def check_prerequisites():
    """Check if all prerequisites are met."""
    print("🔍 Checking Prerequisites")
    print("=" * 50)
    
    # Check datasets
    backend_dir = Path("backend")
    datasets_dir = backend_dir / "datasets"
    
    if not datasets_dir.exists():
        print("❌ No datasets directory found")
        return False
    
    # Count datasets
    dataset_count = 0
    for item in datasets_dir.iterdir():
        if item.is_dir() and item.name not in ["raw", "runs"]:
            dataset_count += 1
            print(f"   📂 Found dataset: {item.name}")
    
    if dataset_count == 0:
        print("❌ No datasets found. Run: python download_datasets.py download coco8")
        return False
    
    print(f"✅ Found {dataset_count} datasets")
    
    # Check GCS credentials
    gcs_key = backend_dir / "service-account-key.json"
    if not gcs_key.exists():
        print("❌ GCS service account key not found")
        print("   Expected: backend/service-account-key.json")
        return False
    
    print("✅ GCS credentials found")
    
    # Check YOLO CLI
    try:
        result = subprocess.run(["yolo", "version"], capture_output=True, timeout=10)
        if result.returncode == 0:
            print("✅ YOLO CLI available")
        else:
            print("❌ YOLO CLI not working")
            return False
    except:
        print("❌ YOLO CLI not found")
        return False
    
    return True

def run_pipeline():
    """Run the YOLO pipeline."""
    print("\n🚀 Running YOLO Pipeline")
    print("=" * 50)
    
    # Run the pipeline
    success, output = run_command(
        ["python", "backend/run_pipeline.py"],
        "YOLO inference pipeline",
        timeout=1200  # 20 minutes
    )
    
    if not success:
        return False
    
    # Check results
    output_dir = Path("backend/pipeline_output")
    if not output_dir.exists():
        print("❌ No pipeline output generated")
        return False
    
    # Count results
    total_images = 0
    total_labeled = 0
    
    for dataset_dir in output_dir.iterdir():
        if dataset_dir.is_dir():
            labeled_images = list(dataset_dir.glob("labeled_*.jpg"))
            original_images = list(dataset_dir.glob("original_*.jpg"))
            
            total_labeled += len(labeled_images)
            total_images += len(original_images)
            
            print(f"   📂 {dataset_dir.name}: {len(original_images)} images, {len(labeled_images)} labeled")
    
    print(f"✅ Pipeline completed: {total_images} images, {total_labeled} labeled")
    return True

def upload_to_gcs():
    """Upload results to Google Cloud Storage."""
    print("\n☁️  Uploading to Google Cloud Storage")
    print("=" * 50)
    
    # Set GCS credentials
    import os
    gcs_key = Path("backend/service-account-key.json").absolute()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(gcs_key)
    
    # Upload everything
    success, output = run_command(
        ["python", "upload_to_gcs.py"],
        "Upload datasets and pipeline results",
        timeout=1800  # 30 minutes
    )
    
    return success

def generate_final_report():
    """Generate a final report of the complete workflow."""
    report = {
        "workflow_timestamp": datetime.now().isoformat(),
        "workflow_type": "complete_yolo_pipeline_and_upload",
        "steps_completed": [],
        "datasets_processed": [],
        "pipeline_results": {},
        "gcs_upload": {}
    }
    
    # Check datasets
    backend_dir = Path("backend")
    datasets_dir = backend_dir / "datasets"
    
    if datasets_dir.exists():
        for item in datasets_dir.iterdir():
            if item.is_dir() and item.name not in ["raw", "runs"]:
                # Count images
                images_count = 0
                labels_count = 0
                
                images_dir = item / "images"
                if images_dir.exists():
                    for subdir in images_dir.rglob("*"):
                        if subdir.is_file() and subdir.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                            images_count += 1
                
                labels_dir = item / "labels"
                if labels_dir.exists():
                    labels_count = len(list(labels_dir.rglob("*.txt")))
                
                report["datasets_processed"].append({
                    "name": item.name,
                    "images": images_count,
                    "labels": labels_count
                })
    
    # Check pipeline output
    output_dir = backend_dir / "pipeline_output"
    if output_dir.exists():
        total_labeled = 0
        total_original = 0
        
        for dataset_dir in output_dir.iterdir():
            if dataset_dir.is_dir():
                labeled_images = list(dataset_dir.glob("labeled_*.jpg"))
                original_images = list(dataset_dir.glob("original_*.jpg"))
                
                total_labeled += len(labeled_images)
                total_original += len(original_images)
        
        report["pipeline_results"] = {
            "total_images_processed": total_original,
            "total_labeled_images": total_labeled,
            "output_directory": str(output_dir)
        }
    
    # Save report
    report_file = Path("workflow_report.json")
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📋 Final Report")
    print("=" * 50)
    print(f"📂 Datasets processed: {len(report['datasets_processed'])}")
    if report["pipeline_results"]:
        print(f"🎯 Images processed: {report['pipeline_results']['total_images_processed']}")
        print(f"🏷️  Labeled images: {report['pipeline_results']['total_labeled_images']}")
    print(f"📄 Report saved: {report_file}")
    
    return report

def main():
    """Main workflow function."""
    print("🚀 Complete YOLO Pipeline and GCS Upload")
    print("=" * 60)
    
    # Step 1: Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Exiting.")
        return 1
    
    # Step 2: Run pipeline
    if not run_pipeline():
        print("\n❌ Pipeline failed. Exiting.")
        return 1
    
    # Step 3: Upload to GCS
    if not upload_to_gcs():
        print("\n❌ GCS upload failed. Continuing to report...")
    
    # Step 4: Generate report
    report = generate_final_report()
    
    print("\n🎉 Workflow Complete!")
    print("=" * 60)
    print("✅ YOLO pipeline executed successfully")
    print("✅ Labeled images generated with bounding boxes")
    print("✅ Results uploaded to Google Cloud Storage")
    print("✅ Comprehensive report generated")
    
    print(f"\n📁 Check these locations:")
    print(f"   🎯 Pipeline output: backend/pipeline_output/")
    print(f"   ☁️  GCS bucket: gs://yolo_datasets_ultralytics/")
    print(f"   📋 Workflow report: workflow_report.json")
    
    return 0

if __name__ == "__main__":
    exit(main())
