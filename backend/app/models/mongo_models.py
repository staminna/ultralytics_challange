from typing import List, Optional
from pydantic import BaseModel, Field
from beanie import Document, Link, PydanticObjectId
from bson import ObjectId

class ClassDefinition(Document):
    id: PydanticObjectId = Field(default_factory=PydanticObjectId, alias="_id")
    name: str
    dataset_id: PydanticObjectId

    class Settings:
        name = "class_definitions"

class Label(Document):
    id: PydanticObjectId = Field(default_factory=PydanticObjectId, alias="_id")
    class_id: PydanticObjectId
    x_center: float
    y_center: float
    width: float
    height: float

    class Settings:
        name = "labels"

class Image(Document):
    id: PydanticObjectId = Field(default_factory=PydanticObjectId, alias="_id")
    dataset_id: PydanticObjectId
    file_name: str
    gcs_path: str
    width: int
    height: int
    labels: List[Link[Label]] = []

    class Settings:
        name = "images"

class Dataset(Document):
    id: PydanticObjectId = Field(default_factory=PydanticObjectId, alias="_id")
    name: str
    description: Optional[str] = None
    format: Optional[str] = None  # e.g., "yolo", "coco", etc.
    file_hash: Optional[str] = None
    gcs_path: Optional[str] = None
    metadata: Optional[dict] = None  # For storing processing status, counts, etc.
    images: List[Link[Image]] = []
    classes: List[Link[ClassDefinition]] = []

    class Settings:
        name = "datasets"
