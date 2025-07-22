import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from functools import lru_cache

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
    
    # Dataset settings
    SUPPORTED_IMAGE_FORMATS: list = ["jpg", "jpeg", "png"]
    MAX_IMAGE_SIZE_MB: int = 10  # Maximum image size in MB
    
    class Config:
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get application settings as singleton."""
    return Settings()
