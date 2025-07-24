#!/usr/bin/env python3
"""
Upload all YOLO datasets found in the datasets directory.
This script will upload both ZIP files and create ZIPs from directories.
"""

import os
import tempfile
import time
import zipfile
from pathlib import Path

import requests

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
DATASETS_DIR = Path("backend/datasets")

def create_zip_from_directory(dir_path: Path, output_path: Path) -> bool:
    """Create a ZIP file from a directory."""
    try:
        print(f"📦 Creating ZIP from directory: {dir_path.name}")
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    # Calculate relative path from the directory
                    arcname = file_path.relative_to(dir_path)
                    zipf.write(file_path, arcname)
                    
        print(f"  ✅ ZIP created: {output_path.name} ({output_path.stat().st_size / 1024 / 1024:.1f} MB)")
        return True
        
    except Exception as e:
        print(f"  ❌ Failed to create ZIP: {e}")
        return False

def upload_yolo_dataset(zip_path: Path, dataset_name: str) -> dict:
    """Upload a YOLO dataset ZIP file to the API."""
    try:
        print(f"🚀 Uploading dataset: {dataset_name}")
        print(f"   File: {zip_path.name} ({zip_path.stat().st_size / 1024 / 1024:.1f} MB)")
        
        # Prepare the request
        url = f"{API_BASE_URL}/datasets/import/yolo"
        
        with open(zip_path, 'rb') as f:
            files = {'file': (zip_path.name, f, 'application/zip')}
            data = {'dataset_name': dataset_name}
            
            # Upload with timeout
            response = requests.post(url, files=files, data=data, timeout=300)
            
        if response.status_code == 200:
            result = response.json()
            dataset_id = result.get('dataset_id', 'unknown')
            print(f"  ✅ Upload successful!")
            print(f"     Dataset ID: {dataset_id}")
            print(f"     Name: {result.get('name', 'N/A')}")
            print(f"     Images: {result.get('image_count', 0)}")
            return result
        else:
            print(f"  ❌ Upload failed: {response.status_code}")
            print(f"     Response: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"  ⏰ Upload timed out (file too large or server slow)")
        return None
    except Exception as e:
        print(f"  ❌ Upload error: {e}")
        return None

def list_existing_datasets() -> list:
    """Get list of existing datasets to avoid duplicates."""
    try:
        response = requests.get(f"{API_BASE_URL}/datasets/")
        if response.status_code == 200:
            datasets = response.json()
            return [d['name'] for d in datasets]
        return []
    except:
        return []

def main():
    """Main upload process."""
    print("🎯 YOLO Dataset Bulk Upload Tool")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get(f"{API_BASE_URL}/datasets/", timeout=10)
        print("✅ Server is running")
    except Exception as e:
        print(f"❌ Server not running! Error: {e}")
        print("Please start with: python server.py")
        return
    
    # Get existing datasets to avoid duplicates
    existing_datasets = list_existing_datasets()
    print(f"📋 Found {len(existing_datasets)} existing datasets")
    
    if not DATASETS_DIR.exists():
        print(f"❌ Datasets directory not found: {DATASETS_DIR}")
        return
    
    uploaded_count = 0
    skipped_count = 0
    failed_count = 0
    
    # Process all items in datasets directory
    for item in sorted(DATASETS_DIR.iterdir()):
        print(f"\n📂 Processing: {item.name}")
        
        if item.is_file() and item.suffix == '.zip':
            # Handle ZIP files directly
            dataset_name = item.stem.replace('_', ' ').title()
            
            if dataset_name in existing_datasets:
                print(f"  ⏭️  Skipping (already exists): {dataset_name}")
                skipped_count += 1
                continue
                
            result = upload_yolo_dataset(item, dataset_name)
            if result:
                uploaded_count += 1
            else:
                failed_count += 1
                
        elif item.is_dir():
            # Handle directories - create ZIP first
            dataset_name = item.name.replace('_', ' ').title()
            
            if dataset_name in existing_datasets:
                print(f"  ⏭️  Skipping (already exists): {dataset_name}")
                skipped_count += 1
                continue
            
            # Create temporary ZIP file
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
                tmp_zip_path = Path(tmp_file.name)
            
            try:
                if create_zip_from_directory(item, tmp_zip_path):
                    result = upload_yolo_dataset(tmp_zip_path, dataset_name)
                    if result:
                        uploaded_count += 1
                    else:
                        failed_count += 1
                else:
                    failed_count += 1
            finally:
                # Clean up temporary file
                if tmp_zip_path.exists():
                    tmp_zip_path.unlink()
        else:
            print(f"  ⏭️  Skipping (not a ZIP or directory): {item.name}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 UPLOAD SUMMARY")
    print(f"✅ Successfully uploaded: {uploaded_count}")
    print(f"⏭️  Skipped (duplicates): {skipped_count}")
    print(f"❌ Failed uploads: {failed_count}")
    print(f"📁 Total processed: {uploaded_count + skipped_count + failed_count}")
    
    if uploaded_count > 0:
        print(f"\n🎉 {uploaded_count} new datasets uploaded successfully!")
        print("🔍 View them at: http://localhost:8000/docs")
        
        # Wait a moment then show final dataset list
        print("\n⏳ Fetching updated dataset list...")
        time.sleep(2)
        
        try:
            response = requests.get(f"{API_BASE_URL}/datasets/")
            if response.status_code == 200:
                datasets = response.json().get('datasets', [])
                print(f"\n📋 All Datasets ({len(datasets)} total):")
                for i, dataset in enumerate(datasets, 1):
                    print(f"  {i}. {dataset['name']} (ID: {dataset['id'][:8]}...)")
                    print(f"     Images: {dataset.get('image_count', 0)}, Created: {dataset.get('created_at', 'N/A')}")
        except:
            print("   (Could not fetch updated list)")

if __name__ == "__main__":
    main()
