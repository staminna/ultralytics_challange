from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


# Common schemas
class PaginationParams(BaseModel):
    model_config = {"from_attributes": True}
    
    skip: int = 0
    limit: int = 100

# Request schemas
class DatasetBase(BaseModel):
    model_config = {"from_attributes": True}
    
    name: str
    description: Optional[str] = None
    is_public: bool = False

class DatasetCreate(DatasetBase):
    model_config = {"from_attributes": True}
    
    name: str = Field(..., description="Name of the dataset")
    description: Optional[str] = Field(None, description="Description of the dataset")
    is_public: bool = Field(False, description="Whether the dataset is publicly accessible")

class DatasetImportYOLO(BaseModel):
    model_config = {"from_attributes": True}
    
    dataset_name: str = Field(..., description="Name for the new dataset")
    description: Optional[str] = Field(None, description="Description of the dataset")
    is_public: bool = Field(False, description="Whether the dataset is publicly accessible")

# Response schemas
class LabelResponse(BaseModel):
    id: str
    class_id: int
    x_center: float
    y_center: float
    width: float
    height: float
    confidence: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class ImageResponse(BaseModel):
    model_config = {"from_attributes": True}
    
    id: str
    filename: str
    url: str
    width: int
    height: int
    created_at: datetime
    updated_at: datetime
    labels: List[Dict[str, Any]] = []

    class Config:
        orm_mode = True

class DatasetResponse(BaseModel):
    model_config = {"from_attributes": True}
    
    id: str
    name: str
    description: Optional[str] = None
    num_images: int = 0
    num_classes: int = 0
    is_public: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class DatasetListResponse(BaseModel):
    model_config = {"from_attributes": True}
    
    datasets: List[DatasetResponse]
    total: int
    skip: int
    limit: int

class ImageListResponse(BaseModel):
    model_config = {"from_attributes": True}
    
    images: List[ImageResponse]
    total: int
    dataset_id: str

# Status responses
class ImportStatusResponse(BaseModel):
    model_config = {"from_attributes": True}
    
    status: str
    message: str
    progress: Optional[float] = None
    total: Optional[int] = None
    processed: Optional[int] = None
