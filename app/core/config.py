import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "YOLO Dataset Annotation Service"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Google Cloud settings
    PROJECT_ID: str = os.getenv("PROJECT_ID", "your-project-id")
    STORAGE_BUCKET: str = os.getenv("STORAGE_BUCKET", "your-bucket-name")
    
    # Service account credentials
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    # API settings
    API_V1_STR: str = "/api/v1"
    
    # Dataset settings
    MAX_DATASET_SIZE_MB: int = 100 * 1024  # 100GB in MB
    ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".bmp"]
    
    class Config:
        case_sensitive = True
        env_file = ".env"

# Create settings instance
settings = Settings()
