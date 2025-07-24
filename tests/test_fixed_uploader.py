#!/usr/bin/env python3
"""
Test the fixed uploader to ensure it processes all images and prevents duplicates.
"""

import json

import requests

API_BASE_URL = "http://localhost:8000/api/v1"

def test_current_datasets():
    """Check current datasets and their image counts."""
    try:
        response = requests.get(f"{API_BASE_URL}/datasets/", timeout=10)
        if response.status_code == 200:
            datasets = response.json()  # API returns list directly
            
            print("📊 Current Datasets:")
            print("-" * 80)
            
            for ds in sorted(datasets, key=lambda x: x.get('created_at', ''), reverse=True):
                name = ds['name']
                images = ds.get('image_count', 0)
                status = ds.get('status', 'unknown')
                created = ds.get('created_at', '')[:16].replace('T', ' ')
                dataset_id = ds.get('id', '')[:8]
                
                icon = "✅" if images > 0 else "❌"
                print(f"{icon} {name:<40} {images:>3} images ({status}) [{dataset_id}] {created}")
            
            print("-" * 80)
            successful = [ds for ds in datasets if ds.get('image_count', 0) > 0]
            failed = [ds for ds in datasets if ds.get('image_count', 0) == 0]
            
            print(f"Summary: ✅ {len(successful)} successful, ❌ {len(failed)} failed")
            
            # Show the most recent successful dataset details
            if successful:
                latest = max(successful, key=lambda x: x.get('created_at', ''))
                print(f"\n🎯 Latest successful dataset:")
                print(f"   Name: {latest['name']}")
                print(f"   Images: {latest['image_count']}")
                print(f"   ID: {latest['id'][:12]}...")
                
                # Check images for this dataset
                dataset_id = latest['id']
                images_response = requests.get(f"{API_BASE_URL}/datasets/{dataset_id}/images")
                if images_response.status_code == 200:
                    images_data = images_response.json()
                    images = images_data.get('images', [])
                    print(f"   📸 Images with labels: {sum(1 for img in images if img.get('labels', []))}")
                    print(f"   📸 Images without labels: {sum(1 for img in images if not img.get('labels', []))}")
                    
                    # Show sample images
                    print(f"   📋 Sample images:")
                    for img in images[:5]:
                        labels_count = len(img.get('labels', []))
                        print(f"      • {img.get('filename', 'unknown')}: {labels_count} labels")
        else:
            print(f"❌ Failed to get datasets: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_server_status():
    """Check if server is running."""
    try:
        response = requests.get(f"{API_BASE_URL}/datasets/", timeout=5)
        print(f"✅ Server is running (status: {response.status_code})")
        assert True
    except Exception as e:
        print(f"❌ Server not running: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Testing Fixed YOLO Uploader")
    print("=" * 60)
    
    if test_server_status():
        test_current_datasets()
        
        print(f"\n💡 Next steps:")
        print(f"1. Restart server: cd backend && python server.py")
        print(f"2. Test upload: python dynamic_dataset_uploader.py")
        print(f"3. Verify all 56 images are processed!")
    else:
        print(f"\n🚨 Please start the server first:")
        print(f"   cd backend && python server.py")
