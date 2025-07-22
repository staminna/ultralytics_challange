from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

# Base schemas
class LabelBase(BaseModel):
    class_id: int
    x_center: float
    y_center: float
    width: float
    height: float


class ImageBase(BaseModel):
    filename: str


class DatasetBase(BaseModel):
    name: str
    description: Optional[str] = None


# Create schemas
class DatasetCreate(DatasetBase):
    pass


class ImageCreate(ImageBase):
    width: int
    height: int


class LabelCreate(LabelBase):
    pass


# Read schemas
class Label(LabelBase):
    id: str
    image_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True


class Image(ImageBase):
    id: str
    dataset_id: str
    storage_path: str
    width: int
    height: int
    created_at: datetime
    updated_at: datetime
    download_url: Optional[str] = None  # URL for frontend to access the image
    labels: List[Label] = []

    class Config:
        populate_by_name = True


class Dataset(DatasetBase):
    id: str
    storage_path: str
    created_at: datetime
    updated_at: datetime
    image_count: int = 0
    status: str = "pending"  # pending, importing, finalizing, ready, error
    import_progress: int = 0
    error_message: Optional[str] = None
    upload_id: Optional[str] = None
    size_bytes: int = 0

    class Config:
        populate_by_name = True


class DatasetWithImages(Dataset):
    images: List[Image] = []

    class Config:
        populate_by_name = True


# Request schemas for importing YOLO format datasets
class YoloImportRequest(BaseModel):
    dataset_name: str
    description: Optional[str] = None
    class_names: List[str] = []  # Optional class names mapping


# Response schemas
class DatasetListResponse(BaseModel):
    datasets: List[Dataset]
    total: int


class ImageListResponse(BaseModel):
    images: List[Image]
    total: int
    dataset_id: str
