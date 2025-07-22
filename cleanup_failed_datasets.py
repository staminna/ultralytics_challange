#!/usr/bin/env python3
"""
Clean up failed datasets (those with 0 images) to make room for fresh uploads.
"""

import requests
import json

API_BASE_URL = "http://localhost:8000/api/v1"

def cleanup_failed_datasets():
    """Remove datasets with 0 images."""
    try:
        # Get all datasets
        response = requests.get(f"{API_BASE_URL}/datasets/", timeout=10)
        if response.status_code != 200:
            print(f"❌ Failed to get datasets: {response.status_code}")
            return
            
        datasets = response.json().get('datasets', [])
        
        print(f"📊 Found {len(datasets)} total datasets")
        
        # Find failed datasets (0 images)
        failed_datasets = [ds for ds in datasets if ds.get('image_count', 0) == 0]
        successful_datasets = [ds for ds in datasets if ds.get('image_count', 0) > 0]
        
        print(f"✅ Successful datasets: {len(successful_datasets)}")
        print(f"❌ Failed datasets: {len(failed_datasets)}")
        
        if not failed_datasets:
            print("🎉 No failed datasets to clean up!")
            return
        
        print("\n🗑️  Failed datasets to remove:")
        for ds in failed_datasets:
            name = ds['name']
            created = ds.get('created_at', '')[:10]
            dataset_id = ds.get('id', '')[:8]
            print(f"   • {name} - {created} [{dataset_id}]")
        
        # Note: We would need a DELETE endpoint to actually remove them
        # For now, just list them
        print(f"\n⚠️  Note: DELETE endpoint not implemented yet.")
        print(f"   These {len(failed_datasets)} failed datasets are taking up space.")
        print(f"   Consider implementing DELETE /api/v1/datasets/{{id}} endpoint.")
        
        print(f"\n✅ Successful datasets with images:")
        for ds in successful_datasets:
            name = ds['name']
            images = ds.get('image_count', 0)
            created = ds.get('created_at', '')[:10]
            print(f"   • {name}: {images} images - {created}")
        
    except Exception as e:
        print(f"❌ Cleanup error: {e}")

if __name__ == "__main__":
    cleanup_failed_datasets()
