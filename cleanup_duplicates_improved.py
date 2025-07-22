#!/usr/bin/env python3
"""Clean up duplicate datasets with improved timeout handling."""

import json
import time
from collections import defaultdict

import requests

API_BASE_URL = "http://localhost:8000/api/v1"

def get_all_datasets():
    """Get all datasets."""
    try:
        response = requests.get(f"{API_BASE_URL}/datasets/", timeout=30)
        if response.status_code == 200:
            return response.json().get('datasets', [])
    except Exception as e:
        print(f"Error fetching datasets: {e}")
    return []

def delete_dataset(dataset_id, dataset_name="", image_count=0):
    """Delete a dataset by ID with extended timeout."""
    try:
        print(f"  🗑️  Deleting {dataset_name} ({image_count} images)...")
        
        # Use much longer timeout for datasets with many images
        timeout = max(60, image_count * 2)  # At least 60s, 2s per image
        
        response = requests.delete(
            f"{API_BASE_URL}/datasets/{dataset_id}", 
            timeout=timeout
        )
        
        if response.status_code == 200:
            print(f"  ✅ Successfully deleted {dataset_name}")
            return True
        else:
            print(f"  ❌ Failed to delete {dataset_name}: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"  ⏱️  Timeout deleting {dataset_name} (may still be processing)")
        return False
    except Exception as e:
        print(f"  ❌ Error deleting {dataset_name}: {e}")
        return False

def cleanup_duplicates():
    """Clean up duplicate datasets, keeping the best version of each."""
    datasets = get_all_datasets()
    
    if not datasets:
        print("❌ No datasets found or server not responding")
        return
    
    print(f"🧹 Cleaning up {len(datasets)} datasets...")
    print("=" * 60)
    
    # Group datasets by normalized name
    groups = defaultdict(list)
    for ds in datasets:
        # Normalize name for grouping
        name = ds['name'].lower()
        name = name.replace('complete', '').replace('yolo', '').replace('items', '').replace('50', '')
        name = ' '.join(name.split())  # Remove extra spaces
        
        groups[name].append(ds)
    
    to_delete = []
    to_keep = []
    
    for group_name, group_datasets in groups.items():
        if len(group_datasets) > 1:
            print(f"\n📦 Group: '{group_name}' ({len(group_datasets)} datasets)")
            
            # Sort by image count (desc), then by creation date (desc)
            sorted_datasets = sorted(
                group_datasets, 
                key=lambda x: (x.get('image_count', 0), x.get('created_at', '')), 
                reverse=True
            )
            
            # Keep the best one (highest image count, most recent)
            best = sorted_datasets[0]
            to_keep.append(best)
            
            print(f"  ✅ KEEP: {best['name']} ({best.get('image_count', 0)} images)")
            
            # Mark others for deletion
            for ds in sorted_datasets[1:]:
                to_delete.append(ds)
                print(f"  ❌ DELETE: {ds['name']} ({ds.get('image_count', 0)} images)")
        else:
            # Single dataset, keep it
            to_keep.append(group_datasets[0])
    
    print(f"\n📊 Summary:")
    print(f"  • Keep: {len(to_keep)} datasets")
    print(f"  • Delete: {len(to_delete)} datasets")
    
    if to_delete:
        print(f"\n⚠️  About to delete {len(to_delete)} duplicate datasets.")
        print("⏱️  Note: Large datasets may take several minutes to delete.")
        confirm = input("Continue? (y/N): ").lower().strip()
        
        if confirm == 'y':
            deleted_count = 0
            failed_count = 0
            
            for i, ds in enumerate(to_delete, 1):
                print(f"\n[{i}/{len(to_delete)}] Processing: {ds['name']}")
                
                if delete_dataset(ds['id'], ds['name'], ds.get('image_count', 0)):
                    deleted_count += 1
                    # Small delay between deletions to avoid overwhelming the server
                    time.sleep(2)
                else:
                    failed_count += 1
            
            print(f"\n🎉 Cleanup complete!")
            print(f"  ✅ Successfully deleted: {deleted_count} datasets")
            print(f"  ❌ Failed to delete: {failed_count} datasets")
            
            if deleted_count > 0:
                print("\n⏱️  Waiting 5 seconds for server to update...")
                time.sleep(5)
                
                # Show final state
                remaining = get_all_datasets()
                print(f"\n📋 Remaining datasets: {len(remaining)}")
                for ds in sorted(remaining, key=lambda x: x.get('created_at', ''), reverse=True)[:10]:
                    print(f"  • {ds['name']}: {ds.get('image_count', 0)} images")
        else:
            print("❌ Cleanup cancelled")
    else:
        print("✅ No duplicates found!")

if __name__ == "__main__":
    cleanup_duplicates()
