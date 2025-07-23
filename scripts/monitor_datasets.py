#!/usr/bin/env python3
"""
Monitor datasets and show their status.
"""

import time

import requests

API_BASE_URL = "http://localhost:8000/api/v1"

def monitor_datasets():
    """Monitor dataset status."""
    try:
        response = requests.get(f"{API_BASE_URL}/datasets/", timeout=10)
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            return
            
        datasets = response.json().get('datasets', [])
        
        print(f"📊 Dataset Status ({len(datasets)} total)")
        print("-" * 80)
        
        successful = 0
        failed = 0
        pending = 0
        
        for ds in sorted(datasets, key=lambda x: x.get('created_at', ''), reverse=True):
            name = ds['name'][:30]  # Truncate long names
            images = ds.get('image_count', 0)
            status = ds.get('status', 'unknown')
            created = ds.get('created_at', '')[:16].replace('T', ' ')
            dataset_id = ds.get('id', '')[:8]
            
            if images > 0:
                icon = "✅"
                successful += 1
            elif status == 'pending':
                icon = "⏳"
                pending += 1
            else:
                icon = "❌"
                failed += 1
            
            print(f"{icon} {name:<30} {images:>3} imgs {status:<8} {created} [{dataset_id}]")
        
        print("-" * 80)
        print(f"Summary: ✅ {successful} successful, ❌ {failed} failed, ⏳ {pending} pending")
        
    except Exception as e:
        print(f"❌ Monitor error: {e}")

if __name__ == "__main__":
    monitor_datasets()
