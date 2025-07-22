from google.cloud import firestore, storage
from google.cloud.exceptions import NotFound
import os
from functools import lru_cache
from fastapi import HTTPException
from .config import get_settings

settings = get_settings()

@lru_cache()
def get_firestore_client():
    """Get a Firestore client instance."""
    try:
        # If running locally with credentials file
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            return firestore.Client()
        # If running on GCP (e.g., Cloud Run)
        return firestore.Client(project=settings.GCP_PROJECT_ID)
    except Exception as e:
        print(f"Error initializing Firestore client: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to Firestore: {str(e)}")

@lru_cache()
def get_storage_client():
    """Get a Google Cloud Storage client instance."""
    try:
        # If running locally with credentials file
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            return storage.Client()
        # If running on GCP (e.g., Cloud Run)
        return storage.Client(project=settings.GCP_PROJECT_ID)
    except Exception as e:
        print(f"Error initializing Storage client: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to Cloud Storage: {str(e)}")

def get_storage_bucket():
    """Get the storage bucket for dataset files. Creates the bucket if it doesn't exist."""
    storage_client = get_storage_client()
    bucket_name = settings.GCP_STORAGE_BUCKET
    
    try:
        # Try to get the bucket
        bucket = storage_client.bucket(bucket_name)
        
        # Check if the bucket exists
        if not bucket.exists():
            print(f"Bucket {bucket_name} does not exist, creating it...")
            bucket = storage_client.create_bucket(bucket_name)
            print(f"Bucket {bucket_name} created.")
        
        return bucket
    except Exception as e:
        print(f"Error accessing storage bucket: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to access storage bucket: {str(e)}")
