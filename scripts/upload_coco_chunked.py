#!/usr/bin/env python3
"""
Chunked Upload Script for Large COCO Dataset

Uploads the 18GB coco-train2017-images.zip file using chunked upload.
This script handles the complete chunked upload workflow.

Usage:
    python scripts/upload_coco_chunked.py
"""

import requests
import os
import time
import hashlib
from typing import Optional
import uuid

# Configuration
SERVER_URL = "http://localhost:8000"
API_BASE = f"{SERVER_URL}/api/v1"
COCO_FILE_PATH = "/Users/jorgenunes/2026/datasets/coco-train2017-images.zip"
CHUNK_SIZE = 10 * 1024 * 1024  # 10MB chunks for production
DATASET_NAME = "COCO Train 2017 - Chunked Upload"
DATASET_DESCRIPTION = "Large COCO training dataset uploaded via chunked upload (18GB)"


class ChunkedUploader:
    """Handles chunked upload of large files."""
    
    def __init__(self, file_path: str, server_url: str = SERVER_URL):
        self.file_path = file_path
        self.server_url = server_url
        self.api_base = f"{server_url}/api/v1"
        self.file_size = os.path.getsize(file_path)
        self.upload_id = str(uuid.uuid4())
        self.dataset_id = None
        
    def calculate_file_hash(self) -> str:
        """Calculate SHA256 hash of the file for integrity checking."""
        print("📊 Calculating file hash for integrity checking...")
        hash_sha256 = hashlib.sha256()
        
        with open(self.file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        
        file_hash = hash_sha256.hexdigest()
        print(f"✅ File hash: {file_hash}")
        return file_hash
    
    def create_dataset_metadata(self) -> Optional[str]:
        """Create dataset metadata first."""
        print("📋 Creating dataset metadata...")
        
        dataset_data = {
            "name": DATASET_NAME,
            "description": DATASET_DESCRIPTION,
            "format": "yolo"
        }
        
        try:
            response = requests.post(f"{self.api_base}/datasets/", json=dataset_data)
            
            if response.status_code in [200, 201]:
                dataset = response.json()
                dataset_id = dataset["id"]
                print(f"✅ Dataset created with ID: {dataset_id}")
                return dataset_id
            elif response.status_code == 409:
                print("⚠️ Dataset with this name already exists")
                # Try to find existing dataset
                response = requests.get(f"{self.api_base}/datasets/")
                if response.status_code == 200:
                    datasets = response.json()
                    for dataset in datasets:
                        if dataset["name"] == DATASET_NAME:
                            print(f"✅ Using existing dataset ID: {dataset['id']}")
                            return dataset["id"]
                return None
            else:
                print(f"❌ Failed to create dataset: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error creating dataset: {str(e)}")
            return None
    
    def upload_chunks(self, dataset_id: str) -> bool:
        """Upload file in chunks."""
        print(f"🚀 Starting chunked upload...")
        print(f"   File: {os.path.basename(self.file_path)}")
        print(f"   Size: {self.file_size / (1024*1024*1024):.2f} GB")
        print(f"   Chunk size: {CHUNK_SIZE / (1024*1024):.1f} MB")
        
        total_chunks = (self.file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
        print(f"   Total chunks: {total_chunks}")
        
        start_time = time.time()
        
        with open(self.file_path, 'rb') as file:
            for chunk_number in range(total_chunks):
                chunk_data = file.read(CHUNK_SIZE)
                if not chunk_data:
                    break
                
                # Upload chunk
                success = self.upload_single_chunk(
                    dataset_id, chunk_number, total_chunks, chunk_data
                )
                
                if not success:
                    print(f"❌ Failed to upload chunk {chunk_number + 1}")
                    return False
                
                # Progress update
                progress = ((chunk_number + 1) / total_chunks) * 100
                elapsed = time.time() - start_time
                eta = (elapsed / (chunk_number + 1)) * (total_chunks - chunk_number - 1)
                
                print(f"📈 Progress: {progress:.1f}% ({chunk_number + 1}/{total_chunks}) "
                      f"- ETA: {eta/60:.1f}m")
        
        total_time = time.time() - start_time
        print(f"✅ Upload completed in {total_time/60:.1f} minutes")
        return True
    
    def upload_single_chunk(self, dataset_id: str, chunk_number: int, 
                          total_chunks: int, chunk_data: bytes) -> bool:
        """Upload a single chunk."""
        try:
            files = {
                "chunk_file": (f"chunk_{chunk_number}", chunk_data, "application/octet-stream")
            }
            
            params = {
                "upload_id": self.upload_id,
                "chunk_number": chunk_number,
                "total_chunks": total_chunks
            }
            
            response = requests.post(
                f"{self.api_base}/datasets/{dataset_id}/chunks",
                files=files,
                params=params,
                timeout=60  # 1 minute timeout per chunk
            )
            
            if response.status_code in [200, 201]:
                return True
            else:
                print(f"❌ Chunk {chunk_number + 1} failed: {response.status_code} - {response.text[:100]}")
                return False
                
        except requests.exceptions.Timeout:
            print(f"❌ Chunk {chunk_number + 1} timed out")
            return False
        except Exception as e:
            print(f"❌ Chunk {chunk_number + 1} error: {str(e)}")
            return False
    
    def check_import_status(self, dataset_id: str):
        """Check the import status after upload."""
        print("🔍 Checking import status...")
        
        try:
            response = requests.get(f"{self.api_base}/datasets/{dataset_id}/import-status")
            
            if response.status_code == 200:
                status = response.json()
                print(f"📊 Import Status: {status}")
            else:
                print(f"⚠️ Could not check status: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️ Status check error: {str(e)}")
    
    def run_upload(self) -> bool:
        """Run the complete upload process."""
        print("🚀 COCO Dataset Chunked Upload")
        print("=" * 40)
        
        # Check if file exists
        if not os.path.exists(self.file_path):
            print(f"❌ File not found: {self.file_path}")
            return False
        
        # Check server connectivity
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            if response.status_code != 200:
                print("❌ Server is not healthy")
                return False
            print("✅ Server is healthy and ready")
        except Exception as e:
            print(f"❌ Cannot connect to server: {str(e)}")
            return False
        
        # Calculate file hash
        file_hash = self.calculate_file_hash()
        
        # Create dataset metadata
        dataset_id = self.create_dataset_metadata()
        if not dataset_id:
            return False
        
        self.dataset_id = dataset_id
        
        # Upload chunks
        success = self.upload_chunks(dataset_id)
        
        if success:
            print("\n🎉 Upload completed successfully!")
            print(f"   Dataset ID: {dataset_id}")
            print(f"   Upload ID: {self.upload_id}")
            print(f"   File Hash: {file_hash}")
            
            # Check status
            time.sleep(2)  # Wait a bit for processing
            self.check_import_status(dataset_id)
            
            return True
        else:
            print("\n❌ Upload failed")
            return False


def main():
    """Main function."""
    uploader = ChunkedUploader(COCO_FILE_PATH)
    success = uploader.run_upload()
    
    if success:
        print("\n✅ COCO dataset upload completed successfully!")
        print("You can now use the dataset through the API.")
    else:
        print("\n❌ Upload failed. Please check the logs above.")
        exit(1)


if __name__ == "__main__":
    main()
