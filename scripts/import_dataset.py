#!/usr/bin/env python3
"""
Dataset Import Tool

A simple Python script to import YOLO format datasets to the annotation service.

Usage:
    python import_dataset.py path/to/dataset.zip "Dataset Name" --description="Description" --classes=car,person,bicycle
"""

import argparse
import os
import sys
from pathlib import Path

import requests


def import_dataset(zip_path: str, name: str, description: str = None, classes: list = None, api_url: str = "http://localhost:8000"):
    """Import a YOLO dataset via API."""
    
    # Check if zip file exists
    if not os.path.exists(zip_path):
        print(f"❌ Error: ZIP file not found: {zip_path}")
        return False
    
    # Prepare API endpoint
    endpoint = f"{api_url}/api/v1/datasets/import/yolo"
    
    # Prepare form data
    files = {
        'zip_file': ('dataset.zip', open(zip_path, 'rb'), 'application/zip')
    }
    
    data = {
        'dataset_name': name,
        'description': description or f"Imported dataset: {name}"
    }
    
    # Add class names if provided
    if classes:
        for class_name in classes:
            data['class_names'] = class_name
    
    try:
        print(f"🚀 Importing dataset: {name}")
        print(f"📁 ZIP file: {zip_path}")
        print(f"📝 Description: {description}")
        print(f"🏷️  Classes: {classes}")
        print(f"🌐 API endpoint: {endpoint}")
        print()
        
        # Make API request
        response = requests.post(endpoint, files=files, data=data)
        
        # Close file
        files['zip_file'][1].close()
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Dataset imported successfully!")
            print(f"📊 Dataset ID: {result['id']}")
            print(f"📂 Dataset Name: {result['name']}")
            print(f"📍 Storage Path: {result['storage_path']}")
            print(f"⏰ Created: {result['created_at']}")
            print(f"🔄 Status: {result['status']}")
            return True
        else:
            print(f"❌ Error importing dataset:")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Error: Could not connect to API server at {api_url}")
        print("Make sure the server is running with: python backend/server.py")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Import YOLO dataset to annotation service")
    parser.add_argument("zip_path", help="Path to YOLO dataset ZIP file")
    parser.add_argument("name", help="Dataset name")
    parser.add_argument("--description", help="Dataset description")
    parser.add_argument("--classes", help="Comma-separated list of class names")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API server URL")
    
    args = parser.parse_args()
    
    # Parse classes
    classes = []
    if args.classes:
        classes = [cls.strip() for cls in args.classes.split(',')]
    
    # Import dataset
    success = import_dataset(
        zip_path=args.zip_path,
        name=args.name,
        description=args.description,
        classes=classes,
        api_url=args.api_url
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
