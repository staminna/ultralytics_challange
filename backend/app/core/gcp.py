import os
from google.cloud import storage
from functools import lru_cache

from .config import settings

@lru_cache()
def get_storage_client() -> storage.Client:
    """Get a Google Cloud Storage client."""
    # If GOOGLE_APPLICATION_CREDENTIALS is set, the client will use it.
    # Otherwise, it will use the default credentials.
    return storage.Client(project=settings.GCP_PROJECT_ID)

def get_storage_bucket() -> storage.Bucket:
    """Get the storage bucket for the application."""
    client = get_storage_client()
    bucket = client.get_bucket(os.getenv("GCP_STORAGE_BUCKET"))
    return bucket
