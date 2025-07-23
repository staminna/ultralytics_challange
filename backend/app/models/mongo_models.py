from typing import List, Optional
from pydantic import BaseModel, Field
from beanie import Document, Link
from uuid import UUID, uuid4

class ClassDefinition(Document):
    id: UUID = Field(default_factory=uuid4)
    name: str
    dataset_id: UUID

    class Settings:
        name = "class_definitions"

class Label(Document):
    id: UUID = Field(default_factory=uuid4)
    class_id: UUID
    x_center: float
    y_center: float
    width: float
    height: float

    class Settings:
        name = "labels"

class Image(Document):
    id: UUID = Field(default_factory=uuid4)
    dataset_id: UUID
    file_name: str
    gcs_path: str
    width: int
    height: int
    labels: List[Link[Label]] = []

    class Settings:
        name = "images"

class Dataset(Document):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    gcs_path: Optional[str] = None
    images: List[Link[Image]] = []
    classes: List[Link[ClassDefinition]] = []

    class Settings:
        name = "datasets"
