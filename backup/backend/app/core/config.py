import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """Application settings."""
    
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Dataset Annotation Service"
    
    # GCP settings
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "annotation-project")
    GCP_STORAGE_BUCKET: str = os.getenv("GCP_STORAGE_BUCKET", "annotation-datasets")
    
    # MongoDB settings
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    mongodb_name: str = os.getenv("MONGODB_DB", "ultralytics_annotation")
    use_mongodb: bool = os.getenv("USE_MONGODB", "True").lower() == "true"
    
    # Performance settings
    batch_size: int = int(os.getenv("BATCH_SIZE", "50"))  # Number of items to process in a batch
    max_workers: int = int(os.getenv("MAX_WORKERS", "8"))  # Number of worker threads
    
    # Dataset settings
    SUPPORTED_IMAGE_FORMATS: list = ["jpg", "jpeg", "png"]
    MAX_IMAGE_SIZE_MB: int = 10  # Maximum image size in MB
    
    class Config:
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get application settings as singleton."""
    return Settings()
