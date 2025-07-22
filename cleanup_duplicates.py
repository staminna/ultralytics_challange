#!/usr/bin/env python3
"""Clean up duplicate datasets, keeping only the best ones."""

import requests
from collections import defaultdict
import json

API_BASE_URL = "http://localhost:8000/api/v1"

def get_all_datasets():
    """Get all datasets."""
    response = requests.get(f"{API_BASE_URL}/datasets/", timeout=10)
    if response.status_code == 200:
        return response.json().get('datasets', [])
    return []

def delete_dataset(dataset_id):
    """Delete a dataset by ID."""
    try:
        response = requests.delete(f"{API_BASE_URL}/datasets/{dataset_id}", timeout=10)
        return response.status_code == 200
    except:
        return False

def cleanup_duplicates():
    """Clean up duplicate datasets, keeping the best version of each."""
    datasets = get_all_datasets()
    
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
        confirm = input("Continue? (y/N): ").lower().strip()
        
        if confirm == 'y':
            deleted_count = 0
            for ds in to_delete:
                print(f"Deleting: {ds['name']} ({ds.get('image_count', 0)} images)...")
                if delete_dataset(ds['id']):
                    deleted_count += 1
                    print("  ✅ Deleted")
                else:
                    print("  ❌ Failed to delete")
            
            print(f"\n🎉 Cleanup complete! Deleted {deleted_count}/{len(to_delete)} datasets")
            
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
