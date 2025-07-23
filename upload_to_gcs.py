#!/usr/bin/env python3
"""
Upload YOLO Datasets and Pipeline Results to Google Cloud Storage

This script uploads:
1. Original YOLO datasets (images + labels)
2. Pipeline output (labeled images with bounding boxes)
3. JSON summaries and metadata
"""
import os
import sys
from pathlib import Path
from google.cloud import storage
import json
from datetime import datetime
import mimetypes

class GCSUploader:
    def __init__(self, bucket_name="yolo_datasets_ultralytics"):
        """Initialize GCS client and bucket."""
        self.bucket_name = bucket_name
        self.client = None
        self.bucket = None
        
        # Set up GCS credentials automatically
        self._setup_credentials()
        
        # Initialize GCS client
        try:
            self.client = storage.Client()
            self.bucket = self.client.bucket(bucket_name)
            print(f"✅ Connected to GCS bucket: {bucket_name}")
        except Exception as e:
            print(f"❌ Failed to connect to GCS: {e}")
            print("   Make sure your service account key is valid")
            sys.exit(1)
    
    def _setup_credentials(self):
        """Set up GCS credentials from service account key."""
        # Look for service account key in common locations
        possible_paths = [
            Path("backend/service-account-key.json"),
            Path("service-account-key.json"),
            Path("backend/.env"),  # Check if path is in .env file
        ]
        
        credentials_path = None
        
        for path in possible_paths:
            if path.exists() and path.name.endswith('.json'):
                credentials_path = path.absolute()
                break
        
        if not credentials_path:
            print("❌ Service account key not found!")
            print("   Expected locations:")
            for path in possible_paths[:2]:  # Don't show .env
                print(f"     - {path}")
            print("   Please ensure your service account key file exists.")
            sys.exit(1)
        
        # Set environment variable
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path)
        print(f"🔑 Using credentials: {credentials_path.name}")
    
    def upload_file(self, local_path, gcs_path, content_type=None):
        """Upload a single file to GCS."""
        try:
            if not content_type:
                content_type, _ = mimetypes.guess_type(str(local_path))
                if not content_type:
                    content_type = 'application/octet-stream'
            
            blob = self.bucket.blob(gcs_path)
            blob.upload_from_filename(str(local_path), content_type=content_type)
            
            print(f"   ✅ {local_path.name} → gs://{self.bucket_name}/{gcs_path}")
            return True
            
        except Exception as e:
            print(f"   ❌ Failed to upload {local_path.name}: {e}")
            return False
    
    def upload_directory(self, local_dir, gcs_prefix, file_extensions=None):
        """Upload all files in a directory to GCS."""
        local_dir = Path(local_dir)
        if not local_dir.exists():
            print(f"❌ Directory not found: {local_dir}")
            return 0, 0
        
        if file_extensions is None:
            file_extensions = ['.jpg', '.jpeg', '.png', '.txt', '.json', '.yaml', '.yml']
        
        uploaded = 0
        failed = 0
        
        print(f"\n📁 Uploading {local_dir.name}/ to gs://{self.bucket_name}/{gcs_prefix}/")
        
        for file_path in local_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in file_extensions:
                # Create relative path for GCS
                relative_path = file_path.relative_to(local_dir)
                gcs_path = f"{gcs_prefix}/{relative_path}"
                
                if self.upload_file(file_path, gcs_path):
                    uploaded += 1
                else:
                    failed += 1
        
        print(f"📊 {local_dir.name}: {uploaded} uploaded, {failed} failed")
        return uploaded, failed
    
    def upload_yolo_datasets(self):
        """Upload original YOLO datasets."""
        backend_dir = Path("backend")
        datasets_dir = backend_dir / "datasets"
        
        if not datasets_dir.exists():
            print("❌ No datasets directory found")
            return 0, 0
        
        total_uploaded = 0
        total_failed = 0
        
        print("\n🚀 Uploading YOLO Datasets")
        print("=" * 50)
        
        # Upload each dataset
        for dataset_dir in datasets_dir.iterdir():
            if dataset_dir.is_dir() and dataset_dir.name not in ["raw", "runs"]:
                dataset_name = dataset_dir.name
                gcs_prefix = f"datasets/original/{dataset_name}"
                
                uploaded, failed = self.upload_directory(dataset_dir, gcs_prefix)
                total_uploaded += uploaded
                total_failed += failed
        
        # Upload YAML configs
        raw_dir = datasets_dir / "raw"
        if raw_dir.exists():
            uploaded, failed = self.upload_directory(raw_dir, "datasets/configs")
            total_uploaded += uploaded
            total_failed += failed
        
        return total_uploaded, total_failed
    
    def upload_pipeline_output(self):
        """Upload pipeline results with labeled images."""
        backend_dir = Path("backend")
        output_dir = backend_dir / "pipeline_output"
        
        if not output_dir.exists():
            print("❌ No pipeline output found")
            return 0, 0
        
        print("\n🎯 Uploading Pipeline Results")
        print("=" * 50)
        
        # Upload all pipeline output
        gcs_prefix = f"pipeline_results/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        uploaded, failed = self.upload_directory(output_dir, gcs_prefix)
        
        return uploaded, failed
    
    def create_upload_summary(self, datasets_stats, pipeline_stats):
        """Create and upload a summary of the upload."""
        summary = {
            "upload_timestamp": datetime.now().isoformat(),
            "bucket": self.bucket_name,
            "datasets": {
                "uploaded": datasets_stats[0],
                "failed": datasets_stats[1]
            },
            "pipeline_results": {
                "uploaded": pipeline_stats[0], 
                "failed": pipeline_stats[1]
            },
            "total_files": datasets_stats[0] + pipeline_stats[0],
            "total_failed": datasets_stats[1] + pipeline_stats[1]
        }
        
        # Save locally
        summary_file = Path("upload_summary.json")
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Upload to GCS
        gcs_path = f"upload_summaries/upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.upload_file(summary_file, gcs_path, "application/json")
        
        # Clean up local file
        summary_file.unlink()
        
        return summary
    
    def list_bucket_contents(self, prefix=""):
        """List contents of the bucket."""
        print(f"\n📋 Bucket Contents: gs://{self.bucket_name}/{prefix}")
        print("-" * 60)
        
        blobs = self.client.list_blobs(self.bucket, prefix=prefix)
        count = 0
        
        for blob in blobs:
            size_mb = blob.size / (1024 * 1024) if blob.size else 0
            print(f"  📄 {blob.name} ({size_mb:.2f} MB)")
            count += 1
            
            if count >= 20:  # Limit output
                print(f"  ... and {len(list(self.client.list_blobs(self.bucket, prefix=prefix))) - 20} more files")
                break
        
        if count == 0:
            print("  (empty)")
    
    def verify_uploads(self):
        """Verify that uploads were successful."""
        print("\n🔍 Verifying Uploads")
        print("=" * 50)
        
        # Check datasets
        datasets_blobs = list(self.client.list_blobs(self.bucket, prefix="datasets/"))
        print(f"📂 Original datasets: {len(datasets_blobs)} files")
        
        # Check pipeline results
        pipeline_blobs = list(self.client.list_blobs(self.bucket, prefix="pipeline_results/"))
        print(f"🎯 Pipeline results: {len(pipeline_blobs)} files")
        
        # Check summaries
        summary_blobs = list(self.client.list_blobs(self.bucket, prefix="upload_summaries/"))
        print(f"📋 Upload summaries: {len(summary_blobs)} files")
        
        return len(datasets_blobs), len(pipeline_blobs), len(summary_blobs)

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload YOLO datasets to Google Cloud Storage")
    parser.add_argument("--bucket", default="yolo_datasets_ultralytics",
                       help="GCS bucket name")
    parser.add_argument("--datasets-only", action="store_true",
                       help="Upload only original datasets")
    parser.add_argument("--pipeline-only", action="store_true", 
                       help="Upload only pipeline results")
    parser.add_argument("--list", action="store_true",
                       help="List bucket contents")
    parser.add_argument("--verify", action="store_true",
                       help="Verify uploads")
    
    args = parser.parse_args()
    
    print("☁️  Google Cloud Storage Uploader")
    print("=" * 50)
    
    # Initialize uploader
    uploader = GCSUploader(args.bucket)
    
    if args.list:
        uploader.list_bucket_contents()
        return 0
    
    if args.verify:
        uploader.verify_uploads()
        return 0
    
    # Upload datasets and pipeline results
    datasets_stats = (0, 0)
    pipeline_stats = (0, 0)
    
    if not args.pipeline_only:
        datasets_stats = uploader.upload_yolo_datasets()
    
    if not args.datasets_only:
        pipeline_stats = uploader.upload_pipeline_output()
    
    # Create summary
    if datasets_stats != (0, 0) or pipeline_stats != (0, 0):
        summary = uploader.create_upload_summary(datasets_stats, pipeline_stats)
        
        print("\n📊 Upload Summary")
        print("=" * 50)
        print(f"✅ Total files uploaded: {summary['total_files']}")
        print(f"❌ Total files failed: {summary['total_failed']}")
        print(f"📁 Original datasets: {datasets_stats[0]} files")
        print(f"🎯 Pipeline results: {pipeline_stats[0]} files")
        print(f"☁️  Bucket: gs://{args.bucket}")
        
        if summary['total_failed'] == 0:
            print("\n🎉 All uploads completed successfully!")
        else:
            print(f"\n⚠️  {summary['total_failed']} files failed to upload")
    
    return 0

if __name__ == "__main__":
    exit(main())
