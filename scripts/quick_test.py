#!/usr/bin/env python3
"""Quick test to check server and datasets."""

import requests


def test_server():
    try:
        response = requests.get("http://localhost:8000/api/v1/datasets/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            datasets = data.get('datasets', [])
            
            print(f"✅ Server is running! Found {len(datasets)} datasets:")
            print("-" * 60)
            
            for ds in sorted(datasets, key=lambda x: x.get('created_at', ''), reverse=True)[:10]:
                name = ds['name'][:35]
                images = ds.get('image_count', 0)
                created = ds.get('created_at', '')[:16].replace('T', ' ')
                
                icon = "✅" if images > 0 else "❌"
                print(f"{icon} {name:<35} {images:>3} images  {created}")
            
            # Count successful datasets
            successful = [ds for ds in datasets if ds.get('image_count', 0) > 0]
            print(f"\n📊 Summary: {len(successful)}/{len(datasets)} datasets have images")
            
            # Find London Hotels datasets
            london_datasets = [ds for ds in datasets if 'london' in ds['name'].lower() and 'hotel' in ds['name'].lower()]
            if london_datasets:
                print(f"\n🏨 London Hotels datasets:")
                for ds in london_datasets:
                    print(f"   • {ds['name']}: {ds.get('image_count', 0)} images")
            
            return True
        else:
            print(f"❌ Server error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server not accessible: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Quick Server Test")
    print("=" * 40)
    test_server()
