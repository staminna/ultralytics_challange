#!/usr/bin/env python3
"""
Dynamic Dataset Uploader - Automatically detects and uploads ANY dataset directory.
No hardcoded names - works with any YOLO dataset structure.
"""

import os
import requests
import zipfile
import tempfile
from pathlib import Path
import time
import hashlib

API_BASE_URL = "http://localhost:8000/api/v1"
DATASETS_DIR = Path("backend/datasets")

def is_yolo_dataset(path: Path) -> tuple[bool, dict]:
    """Check if a directory contains a valid YOLO dataset structure."""
    if not path.is_dir():
        return False, {}
    
    info = {
        'images': 0,
        'labels': 0,
        'has_train_dir': False,
        'has_images_dir': False,
        'has_labels_dir': False,
        'structure': 'unknown'
    }
    
    # Count all image and label files recursively
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
    
    for file_path in path.rglob('*'):
        if file_path.is_file():
            if file_path.suffix.lower() in image_extensions:
                info['images'] += 1
            elif file_path.suffix.lower() == '.txt' and file_path.name != 'classes.txt':
                info['labels'] += 1
    
    # Check directory structure
    if (path / 'images').exists():
        info['has_images_dir'] = True
        if (path / 'images' / 'train').exists():
            info['has_train_dir'] = True
            info['structure'] = 'standard_yolo'
    
    if (path / 'labels').exists():
        info['has_labels_dir'] = True
    
    # A valid YOLO dataset should have at least some images
    is_valid = info['images'] > 0
    
    return is_valid, info

def create_zip_from_directory(dir_path: Path, output_path: Path) -> bool:
    """Create a ZIP file from any directory."""
    try:
        print(f"📦 Creating ZIP: {dir_path.name}")
        
        file_count = 0
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    # Preserve directory structure in ZIP
                    arcname = file_path.relative_to(dir_path)
                    zipf.write(file_path, arcname)
                    file_count += 1
                    
        size_mb = output_path.stat().st_size / 1024 / 1024
        print(f"  ✅ ZIP created: {size_mb:.1f} MB, {file_count} files")
        return True
        
    except Exception as e:
        print(f"  ❌ ZIP creation failed: {e}")
        return False

def upload_dataset_zip(zip_path: Path, dataset_name: str) -> dict:
    """Upload any dataset ZIP to the API."""
    try:
        size_mb = zip_path.stat().st_size / 1024 / 1024
        print(f"🚀 Uploading: {dataset_name}")
        print(f"   Size: {size_mb:.1f} MB")
        
        url = f"{API_BASE_URL}/datasets/import/yolo"
        
        with open(zip_path, 'rb') as f:
            files = {'zip_file': (zip_path.name, f, 'application/zip')}
            data = {'dataset_name': dataset_name}
            
            # Dynamic timeout based on file size
            timeout = max(60, int(size_mb * 10))  # 10 seconds per MB, minimum 60s
            print(f"   Timeout: {timeout}s")
            
            response = requests.post(url, files=files, data=data, timeout=timeout)
            
        print(f"   Response: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ SUCCESS!")
            print(f"     ID: {result.get('id', 'unknown')[:8]}...")
            print(f"     Images: {result.get('image_count', 0)}")
            return result
        else:
            print(f"  ❌ FAILED: {response.status_code}")
            try:
                error = response.json()
                print(f"     Error: {error}")
            except:
                print(f"     Response: {response.text[:200]}...")
            return None
            
    except requests.exceptions.Timeout:
        print(f"  ⏰ TIMEOUT")
        return None
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return None

def generate_dataset_name(dir_name: str) -> str:
    """Generate a clean dataset name from directory name."""
    # Remove common prefixes/suffixes
    name = dir_name.replace('_dataset', '').replace('_data', '')
    
    # Replace underscores with spaces and title case
    name = name.replace('_', ' ').strip()
    
    # Title case each word
    name = ' '.join(word.capitalize() for word in name.split())
    
    return name

def get_existing_datasets() -> dict:
    """Get existing datasets to prevent duplicates."""
    try:
        response = requests.get(f"{API_BASE_URL}/datasets/", timeout=10)
        if response.status_code == 200:
            datasets = response.json().get('datasets', [])
            existing = {}
            for ds in datasets:
                # Create multiple normalized versions for comparison
                name = ds['name'].lower()
                normalized_variants = [
                    name,
                    name.replace(' ', '_'),
                    name.replace('_', ' '),
                    name.replace('-', '_'),
                    name.replace(' ', '').replace('_', '').replace('-', '')
                ]
                
                for variant in normalized_variants:
                    existing[variant] = {
                        'id': ds['id'],
                        'name': ds['name'],
                        'image_count': ds.get('image_count', 0),
                        'status': ds.get('status', 'unknown'),
                        'created_at': ds.get('created_at', '')
                    }
            return existing
        return {}
    except Exception as e:
        print(f"⚠️  Could not fetch existing datasets: {e}")
        return {}

def should_upload_dataset(dir_name: str, existing_datasets: dict) -> tuple[bool, str]:
    """Check if dataset should be uploaded to prevent duplicates."""
    # Create normalized versions of the directory name
    dir_normalized = dir_name.lower()
    dir_variants = [
        dir_normalized,
        dir_normalized.replace(' ', '_'),
        dir_normalized.replace('_', ' '),
        dir_normalized.replace('-', '_'),
        dir_normalized.replace(' ', '').replace('_', '').replace('-', '')
    ]
    
    # Check against all existing datasets
    for variant in dir_variants:
        if variant in existing_datasets:
            existing = existing_datasets[variant]
            if existing['image_count'] > 0:
                return False, f"Dataset '{existing['name']}' already exists with {existing['image_count']} images"
            else:
                return True, f"Replacing failed dataset '{existing['name']}' (0 images)"
    
    return True, "New dataset"

def scan_and_upload_datasets():
    """Scan for datasets and upload them dynamically."""
    print("🎯 Dynamic Dataset Scanner & Uploader")
    print("=" * 60)
    
    # Check server
    try:
        response = requests.get(f"{API_BASE_URL}/datasets/", timeout=10)
        print("✅ Server is running")
    except Exception as e:
        print(f"❌ Server error: {e}")
        return
    
    if not DATASETS_DIR.exists():
        print(f"❌ Datasets directory not found: {DATASETS_DIR}")
        return
    
    print(f"📂 Scanning: {DATASETS_DIR}")
    
    # Find all potential datasets
    candidates = []
    for item in DATASETS_DIR.iterdir():
        if item.name.startswith('.'):
            continue
            
        if item.is_dir():
            is_valid, info = is_yolo_dataset(item)
            candidates.append({
                'path': item,
                'name': item.name,
                'is_valid': is_valid,
                'info': info
            })
        elif item.is_file() and item.suffix == '.zip':
            candidates.append({
                'path': item,
                'name': item.stem,
                'is_valid': True,  # Assume ZIP files are valid
                'info': {'images': '?', 'labels': '?', 'structure': 'zip_file'}
            })
    
    print(f"📋 Found {len(candidates)} potential datasets:")
    
    # Display candidates
    for i, candidate in enumerate(candidates, 1):
        path = candidate['path']
        info = candidate['info']
        status = "✅ Valid" if candidate['is_valid'] else "❌ Invalid"
        
        if path.is_dir():
            print(f"  {i}. {path.name} - {info['images']} images, {info['labels']} labels ({status})")
        else:
            size_mb = path.stat().st_size / 1024 / 1024
            print(f"  {i}. {path.name} - ZIP file, {size_mb:.1f} MB ({status})")
    
    # Get existing datasets
    existing_datasets = get_existing_datasets()
    
    # Upload valid datasets
    uploaded = 0
    failed = 0
    
    for candidate in candidates:
        if not candidate['is_valid']:
            print(f"\n⏭️  Skipping {candidate['name']}: Not a valid dataset")
            continue
        
        path = candidate['path']
        dataset_name = generate_dataset_name(candidate['name'])
        
        # Check if dataset should be uploaded
        should_upload, reason = should_upload_dataset(dataset_name, existing_datasets)
        if not should_upload:
            print(f"\n⏭️  Skipping {dataset_name}: {reason}")
            continue
        
        print(f"\n📂 Processing: {path.name}")
        print(f"   Generated name: {dataset_name}")
        
        if path.is_file() and path.suffix == '.zip':
            # Upload ZIP directly
            result = upload_dataset_zip(path, dataset_name)
            if result:
                uploaded += 1
            else:
                failed += 1
                
        elif path.is_dir():
            # Create ZIP from directory and upload
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
                tmp_zip_path = Path(tmp_file.name)
            
            try:
                if create_zip_from_directory(path, tmp_zip_path):
                    result = upload_dataset_zip(tmp_zip_path, dataset_name)
                    if result:
                        uploaded += 1
                    else:
                        failed += 1
                else:
                    failed += 1
            finally:
                if tmp_zip_path.exists():
                    tmp_zip_path.unlink()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 UPLOAD SUMMARY")
    print(f"✅ Successfully uploaded: {uploaded}")
    print(f"❌ Failed uploads: {failed}")
    print(f"📁 Total processed: {uploaded + failed}")
    
    if uploaded > 0:
        print(f"\n🎉 {uploaded} datasets uploaded successfully!")
        print("⏳ Waiting for processing...")
        time.sleep(3)
        
        # Show updated dataset list
        try:
            response = requests.get(f"{API_BASE_URL}/datasets/")
            if response.status_code == 200:
                datasets = response.json().get('datasets', [])
                recent_datasets = sorted(datasets, key=lambda x: x.get('created_at', ''), reverse=True)[:5]
                
                print(f"\n📋 Recent Datasets:")
                for ds in recent_datasets:
                    name = ds['name']
                    images = ds.get('image_count', 0)
                    status = ds.get('status', 'unknown')
                    created = ds.get('created_at', '')[:16].replace('T', ' ')
                    print(f"  • {name}: {images} images ({status}) - {created}")
        except:
            print("   (Could not fetch updated list)")

if __name__ == "__main__":
    scan_and_upload_datasets()
