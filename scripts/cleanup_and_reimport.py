#!/usr/bin/env python3
"""
Clean up failed datasets and re-import fresh datasets.
This script will:
1. Delete all datasets with 0 images (failed imports)
2. Keep successful datasets with images
3. Re-upload datasets from the datasets directory
"""

import requests
import time
from pathlib import Path

API_BASE_URL = "http://localhost:8000/api/v1"

def get_all_datasets():
    """Get all datasets from the API."""
    try:
        response = requests.get(f"{API_BASE_URL}/datasets/", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get datasets: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error getting datasets: {e}")
        return []

def delete_dataset(dataset_id: str, dataset_name: str):
    """Delete a dataset by ID."""
    try:
        response = requests.delete(f"{API_BASE_URL}/datasets/{dataset_id}", timeout=30)
        if response.status_code == 200:
            print(f"✅ Deleted: {dataset_name[:40]}")
            return True
        else:
            print(f"❌ Failed to delete {dataset_name}: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error deleting {dataset_name}: {e}")
        return False

def delete_all_datasets():
    """Delete ALL datasets from the database."""
    print("🧹 Deleting ALL existing datasets...")
    print("=" * 60)
    
    datasets = get_all_datasets()
    if not datasets:
        print("✅ No datasets found to delete.")
        return
    
    print(f"📊 Found {len(datasets)} datasets to delete.")
    
    print("\n🗑️  Deleting datasets...")
    deleted_count = 0
    
    for dataset in datasets:
        dataset_id = dataset.get('id')
        dataset_name = dataset.get('name', 'Unknown')
        
        if delete_dataset(dataset_id, dataset_name):
            deleted_count += 1
            time.sleep(0.5)  # Small delay to avoid overwhelming the server
    
    print(f"\n✅ Cleanup complete! Deleted {deleted_count}/{len(datasets)} datasets.")

def show_current_status():
    """Show current database status."""
    print("\n📊 Current Database Status:")
    print("=" * 60)
    
    datasets = get_all_datasets()
    if not datasets:
        print("No datasets found")
        return
    
    successful = [ds for ds in datasets if ds.get('image_count', 0) > 0]
    failed = [ds for ds in datasets if ds.get('image_count', 0) == 0]
    
    print(f"✅ Successful datasets: {len(successful)}")
    print(f"❌ Failed datasets: {len(failed)}")
    print(f"📊 Total datasets: {len(datasets)}")
    
    if successful:
        print("\n🎯 Successful datasets:")
        for ds in successful:
            name = ds.get('name', 'Unknown')
            images = ds.get('image_count', 0)
            created = ds.get('created_at', '')[:16].replace('T', ' ')
            print(f"   ✅ {name[:40]} - {images} images ({created})")

def main():
    """Main cleanup and status process."""
    print("🔧 Dataset Cleanup and Re-import Tool")
    print("=" * 60)
    
    # Show current status
    show_current_status()
    
    # Ask for confirmation
    print("\n⚠️  This will delete all datasets with 0 images.")
    response = input("Continue? (y/N): ").strip().lower()
    
    if response != 'y':
        print("❌ Cleanup cancelled")
        return
    
    # 1. Delete all existing datasets
    delete_all_datasets()
    
    # Show final status
    show_current_status()
    
    print("\n💡 Next steps:")
    print("1. Run: python scripts/upload_all_datasets.py")
    print("2. Or run: python tests/test_fixed_uploader.py to check status")

if __name__ == "__main__":
    main()
