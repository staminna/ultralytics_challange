#!/usr/bin/env python3
"""
Model Deployment to Google Cloud Storage

Deploys trained YOLO models to GCS with versioning and metadata.

Usage:
    python scripts/deploy_model_to_gcs.py --model-path ./runs/train/exp/weights/best.pt --model-name yolo11-custom --version v1.0
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from google.cloud import storage
from google.auth.exceptions import DefaultCredentialsError

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from backend.app.core.gcp import get_storage_bucket
    from backend.app.core.config import get_settings
except ImportError:
    print("❌ Error: Cannot import backend modules. Make sure you're in the project root.")
    sys.exit(1)


class ModelDeployer:
    """Handles model deployment to Google Cloud Storage."""
    
    def __init__(self):
        self.settings = get_settings()
        try:
            self.bucket = get_storage_bucket()
            print(f"✅ Connected to GCS bucket: {self.bucket.name}")
        except DefaultCredentialsError:
            print("❌ Error: Google Cloud credentials not configured.")
            print("   Set GOOGLE_APPLICATION_CREDENTIALS or run 'gcloud auth application-default login'")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error connecting to GCS: {e}")
            sys.exit(1)
    
    def upload_model(
        self, 
        local_model_path: str, 
        model_name: str, 
        version: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Upload a YOLO model to GCS with metadata.
        
        Args:
            local_model_path: Path to the local model file
            model_name: Name of the model (e.g., 'yolo11-custom')
            version: Version string (e.g., 'v1.0')
            description: Optional description of the model
            tags: Optional dictionary of tags/metadata
            
        Returns:
            GCS path of the uploaded model
        """
        # Validate local file exists
        if not os.path.exists(local_model_path):
            raise FileNotFoundError(f"Model file not found: {local_model_path}")
        
        # Generate GCS path
        gcs_model_path = f"models/trained/{model_name}-{version}.pt"
        
        # Upload model file
        print(f"📤 Uploading model: {local_model_path}")
        print(f"📍 Destination: gs://{self.bucket.name}/{gcs_model_path}")
        
        blob = self.bucket.blob(gcs_model_path)
        
        # Set metadata
        metadata = {
            'model_name': model_name,
            'version': version,
            'upload_timestamp': datetime.utcnow().isoformat(),
            'original_path': local_model_path,
            'file_size': str(os.path.getsize(local_model_path))
        }
        
        if description:
            metadata['description'] = description
        
        if tags:
            metadata.update(tags)
        
        blob.metadata = metadata
        
        # Upload the file
        with open(local_model_path, 'rb') as model_file:
            blob.upload_from_file(model_file)
        
        print(f"✅ Model uploaded successfully!")
        print(f"📊 File size: {os.path.getsize(local_model_path) / (1024*1024):.2f} MB")
        
        # Create metadata file
        self._create_metadata_file(gcs_model_path, metadata)
        
        return f"gs://{self.bucket.name}/{gcs_model_path}"
    
    def _create_metadata_file(self, model_path: str, metadata: Dict[str, str]):
        """Create a JSON metadata file alongside the model."""
        metadata_path = model_path.replace('.pt', '_metadata.json')
        metadata_blob = self.bucket.blob(metadata_path)
        
        metadata_json = json.dumps(metadata, indent=2)
        metadata_blob.upload_from_string(metadata_json, content_type='application/json')
        
        print(f"📋 Metadata saved: gs://{self.bucket.name}/{metadata_path}")
    
    def list_models(self, model_name_filter: Optional[str] = None) -> list:
        """List all deployed models."""
        print("📋 Deployed Models:")
        print("-" * 50)
        
        models = []
        blobs = self.bucket.list_blobs(prefix="models/trained/")
        
        for blob in blobs:
            if blob.name.endswith('.pt'):
                if model_name_filter and model_name_filter not in blob.name:
                    continue
                
                models.append({
                    'name': blob.name,
                    'size': blob.size,
                    'created': blob.time_created,
                    'metadata': blob.metadata or {}
                })
                
                print(f"🤖 {blob.name}")
                print(f"   Size: {blob.size / (1024*1024):.2f} MB")
                print(f"   Created: {blob.time_created}")
                if blob.metadata:
                    print(f"   Version: {blob.metadata.get('version', 'unknown')}")
                    print(f"   Description: {blob.metadata.get('description', 'N/A')}")
                print()
        
        return models
    
    def download_model(self, gcs_model_path: str, local_path: str):
        """Download a model from GCS."""
        blob = self.bucket.blob(gcs_model_path)
        
        if not blob.exists():
            raise FileNotFoundError(f"Model not found in GCS: {gcs_model_path}")
        
        print(f"📥 Downloading model: gs://{self.bucket.name}/{gcs_model_path}")
        print(f"📍 Local path: {local_path}")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        blob.download_to_filename(local_path)
        print(f"✅ Model downloaded successfully!")


def main():
    parser = argparse.ArgumentParser(description="Deploy YOLO models to Google Cloud Storage")
    parser.add_argument("--model-path", required=True, help="Path to the local model file")
    parser.add_argument("--model-name", required=True, help="Name of the model")
    parser.add_argument("--version", required=True, help="Version string (e.g., v1.0)")
    parser.add_argument("--description", help="Description of the model")
    parser.add_argument("--tags", help="JSON string of tags/metadata")
    parser.add_argument("--list", action="store_true", help="List deployed models")
    parser.add_argument("--download", help="Download model from GCS (specify GCS path)")
    parser.add_argument("--output", help="Output path for downloaded model")
    
    args = parser.parse_args()
    
    deployer = ModelDeployer()
    
    if args.list:
        deployer.list_models()
        return
    
    if args.download:
        if not args.output:
            print("❌ Error: --output required when downloading")
            sys.exit(1)
        deployer.download_model(args.download, args.output)
        return
    
    # Parse tags if provided
    tags = None
    if args.tags:
        try:
            tags = json.loads(args.tags)
        except json.JSONDecodeError:
            print("❌ Error: Invalid JSON in --tags")
            sys.exit(1)
    
    # Deploy model
    try:
        gcs_path = deployer.upload_model(
            local_model_path=args.model_path,
            model_name=args.model_name,
            version=args.version,
            description=args.description,
            tags=tags
        )
        
        print(f"\n🎉 Model deployment successful!")
        print(f"📍 GCS Path: {gcs_path}")
        print(f"🔗 Use this path to load the model in your applications")
        
    except Exception as e:
        print(f"❌ Error deploying model: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
