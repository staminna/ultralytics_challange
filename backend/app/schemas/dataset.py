import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, ConfigDict


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


class ImageUpdate(BaseModel):
    filename: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class LabelUpdate(BaseModel):
    class_id: Optional[int] = None
    x_center: Optional[float] = None
    y_center: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None


# Read schemas
class Label(LabelBase):
    id: str
    image_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True)


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

    model_config = ConfigDict(populate_by_name=True)


class Dataset(DatasetBase):
    id: str
    format: Optional[str] = None
    file_hash: Optional[str] = None
    gcs_path: Optional[str] = None
    storage_path: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    image_count: int = 0
    status: str = "pending"  # pending, importing, finalizing, ready, error
    import_progress: int = 0
    error_message: Optional[str] = None
    upload_id: Optional[str] = None
    size_bytes: int = 0

    model_config = ConfigDict(populate_by_name=True)


class DatasetWithImages(Dataset):
    images: List[Image] = []

    model_config = ConfigDict(populate_by_name=True)


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


class DeleteResponse(BaseModel):
    message: str
    success: bool = True
