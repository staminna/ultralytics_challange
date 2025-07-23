import os
import shutil
from pathlib import Path
from typing import Optional, Union
from abc import ABC, abstractmethod
from google.cloud import storage
from google.auth.exceptions import DefaultCredentialsError
from functools import lru_cache

from .config import settings


class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    async def upload_file(self, local_path: Path, remote_path: str) -> str:
        """Upload a file and return the storage URL."""
        pass
    
    @abstractmethod
    async def delete_file(self, remote_path: str) -> bool:
        """Delete a file. Returns True if successful."""
        pass
    
    @abstractmethod
    async def file_exists(self, remote_path: str) -> bool:
        """Check if a file exists."""
        pass


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend for development."""
    
    def __init__(self, base_path: str = "storage"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        
        # Create consistent directory structure
        (self.base_path / "datasets").mkdir(exist_ok=True)
        (self.base_path / "models").mkdir(exist_ok=True)
        (self.base_path / "outputs").mkdir(exist_ok=True)
    
    async def upload_file(self, local_path: Path, remote_path: str) -> str:
        """Upload file to local storage."""
        target_path = self.base_path / remote_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(local_path, target_path)
        return f"local://{remote_path}"
    
    async def delete_file(self, remote_path: str) -> bool:
        """Delete file from local storage."""
        try:
            target_path = self.base_path / remote_path
            if target_path.exists():
                target_path.unlink()
                return True
            return False
        except Exception:
            return False
    
    async def file_exists(self, remote_path: str) -> bool:
        """Check if file exists in local storage."""
        target_path = self.base_path / remote_path
        return target_path.exists()


class GCSStorageBackend(StorageBackend):
    """Google Cloud Storage backend for production.
    
    Uses consistent directory structure:
    - datasets/{dataset_id}/images/
    - datasets/{dataset_id}/labels/
    - models/{model_id}/
    - outputs/{output_id}/
    """
    
    def __init__(self, bucket_name: str, project_id: str):
        self.bucket_name = bucket_name
        self.project_id = project_id
        self._client = None
        self._bucket = None
    
    @property
    def client(self) -> storage.Client:
        """Lazy initialization of GCS client."""
        if self._client is None:
            self._client = storage.Client(project=self.project_id)
        return self._client
    
    @property
    def bucket(self) -> storage.Bucket:
        """Lazy initialization of GCS bucket."""
        if self._bucket is None:
            self._bucket = self.client.bucket(self.bucket_name)
        return self._bucket
    
    async def upload_file(self, local_path: Path, remote_path: str) -> str:
        """Upload file to GCS."""
        blob = self.bucket.blob(remote_path)
        blob.upload_from_filename(str(local_path))
        return f"gs://{self.bucket_name}/{remote_path}"
    
    async def delete_file(self, remote_path: str) -> bool:
        """Delete file from GCS."""
        try:
            blob = self.bucket.blob(remote_path)
            blob.delete()
            return True
        except Exception:
            return False
    
    async def file_exists(self, remote_path: str) -> bool:
        """Check if file exists in GCS."""
        try:
            blob = self.bucket.blob(remote_path)
            return blob.exists()
        except Exception:
            return False


@lru_cache()
def get_storage_backend() -> StorageBackend:
    """Get the appropriate storage backend based on configuration."""
    try:
        # Try to initialize GCS if credentials are available
        if hasattr(settings, 'GCP_PROJECT_ID') and hasattr(settings, 'GCP_STORAGE_BUCKET'):
            if settings.GCP_PROJECT_ID and settings.GCP_STORAGE_BUCKET:
                # Test if credentials work
                client = storage.Client(project=settings.GCP_PROJECT_ID)
                # This will raise an exception if credentials are not available
                list(client.list_buckets(max_results=1))
                
                return GCSStorageBackend(
                    bucket_name=settings.GCP_STORAGE_BUCKET,
                    project_id=settings.GCP_PROJECT_ID
                )
    except (DefaultCredentialsError, Exception):
        pass
    
    # Fall back to local storage
    print("Warning: GCS credentials not available, using local storage")
    return LocalStorageBackend(base_path="storage")


# Legacy compatibility functions
def get_storage_client() -> storage.Client:
    """Legacy function for backward compatibility."""
    try:
        return storage.Client(project=settings.GCP_PROJECT_ID)
    except DefaultCredentialsError:
        raise RuntimeError(
            "Google Cloud credentials not configured. "
            "Set GOOGLE_APPLICATION_CREDENTIALS or run 'gcloud auth application-default login'"
        )


def get_storage_bucket() -> storage.Bucket:
    """Legacy function for backward compatibility."""
    client = get_storage_client()
    return client.bucket(settings.GCP_STORAGE_BUCKET)
