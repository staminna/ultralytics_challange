from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID

# Base models for core entities
class ClassDefinitionBase(BaseModel):
    name: str

class LabelBase(BaseModel):
    class_id: UUID
    x_center: float
    y_center: float
    width: float
    height: float

class ImageBase(BaseModel):
    file_name: str
    width: int
    height: int

class DatasetBase(BaseModel):
    name: str
    description: Optional[str] = None

# Schemas for creating new entities
class ClassDefinitionCreate(ClassDefinitionBase):
    pass

class LabelCreate(LabelBase):
    pass

class ImageCreate(ImageBase):
    pass

class DatasetCreate(DatasetBase):
    pass

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
