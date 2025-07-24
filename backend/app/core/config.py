import os
from typing import List

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    # API settings
    LOGLEVEL: str = os.getenv("LOGLEVEL", "info")
    PROJECT_NAME: str = "YOLO Dataset Annotation API by Jorge"
    API_V1_STR: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    # Database settings
    DATABASE_URL: str
    MONGO_DB: str = "ultralytics_annotation"

    # GCP settings
    GCP_PROJECT_ID: str
    GCP_STORAGE_BUCKET: str
    GOOGLE_APPLICATION_CREDENTIALS: str

    # This model_config tells Pydantic to load settings from the .env file
    # located one directory up from the current file's location.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'  # Ignore extra fields from .env that are not in the model
    )


# Create a single instance of the settings to be used throughout the application
settings = Settings()


def get_settings() -> Settings:
    """Get the application settings instance."""
    return settings
