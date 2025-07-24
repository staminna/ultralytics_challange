from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID
from beanie import PydanticObjectId
from datetime import datetime

# Base models for core entities
class ClassDefinitionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Class name must be between 1 and 100 characters")

class LabelBase(BaseModel):
    class_id: UUID
    x_center: float = Field(..., ge=0.0, le=1.0, description="X center coordinate (0.0 to 1.0)")
    y_center: float = Field(..., ge=0.0, le=1.0, description="Y center coordinate (0.0 to 1.0)")
    width: float = Field(..., gt=0.0, le=1.0, description="Width (0.0 to 1.0)")
    height: float = Field(..., gt=0.0, le=1.0, description="Height (0.0 to 1.0)")

class ImageBase(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=255, description="Image filename must be between 1 and 255 characters")
    width: int = Field(..., gt=0, le=50000, description="Image width must be between 1 and 50000 pixels")
    height: int = Field(..., gt=0, le=50000, description="Image height must be between 1 and 50000 pixels")

class DatasetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Dataset name must be between 1 and 255 characters")
    description: Optional[str] = Field(None, max_length=1000, description="Dataset description (optional, max 1000 characters)")

# Schemas for creating new entities
class ClassDefinitionCreate(ClassDefinitionBase):
    pass

class LabelCreate(LabelBase):
    pass

class ImageCreate(ImageBase):
    pass

class DatasetCreate(DatasetBase):
    format: Optional[str] = "yolo"
    file_hash: Optional[str] = None

# Schemas for reading entities (including ID)
class ClassDefinition(ClassDefinitionBase):
    id: UUID
    dataset_id: UUID

    class Config:
        from_attributes = True

class Label(LabelBase):
    id: UUID

    class Config:
        from_attributes = True

class Image(ImageBase):
    id: UUID
    dataset_id: UUID
    gcs_path: str
    labels: List[Label] = []

    class Config:
        from_attributes = True

class Dataset(DatasetBase):
    id: UUID
    gcs_path: Optional[str] = None
    images: List[Image] = []
    classes: List[ClassDefinition] = []

    class Config:
        from_attributes = True

# Import response schema
class DatasetImportResponse(BaseModel):
    """Response schema for dataset import operations."""
    id: str
    name: str
    description: Optional[str] = None
    format: str
    file_hash: str
    processing_status: str
    images_count: int
    labels_count: int
    processed_images: int
    classes_count: int
    original_filename: str
    storage_path: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Response schemas
class DeleteResponse(BaseModel):
    """Response schema for delete operations."""
    message: str


class ImageUpdate(BaseModel):
    """Schema for updating image metadata."""
    filename: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class LabelUpdate(BaseModel):
    """Schema for updating label data."""
    class_id: Optional[int] = None
    x_center: Optional[float] = None
    y_center: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
