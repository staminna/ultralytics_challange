import os
from google.cloud import storage
from google.auth.exceptions import DefaultCredentialsError
from functools import lru_cache

from .config import settings

@lru_cache()
def get_storage_client() -> storage.Client:
    """Get a Google Cloud Storage client."""
    try:
        return storage.Client(project=settings.GCP_PROJECT_ID)
    except DefaultCredentialsError:
        raise RuntimeError(
            "Google Cloud credentials not configured. "
            "Set GOOGLE_APPLICATION_CREDENTIALS or run 'gcloud auth application-default login'"
        )

def get_storage_bucket() -> storage.Bucket:
    """Get the storage bucket for the application."""
    client = get_storage_client()
    return client.bucket(settings.GCP_STORAGE_BUCKET)
