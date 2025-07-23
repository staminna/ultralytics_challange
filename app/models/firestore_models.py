import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BaseFirestoreModel:
    """Base model for Firestore documents"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for Firestore"""
        data = self.dict()
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create model from Firestore document"""
        if not data:
            return None
        return cls(**data)

class Dataset(BaseFirestoreModel, BaseModel):
    """Dataset model"""
    model_config = {
        "from_attributes": True,
        "json_encoders": {
            datetime: lambda dt: dt.isoformat()
        }
    }
    
    name: str
    description: str = ""
    created_by: str = "system"
    is_public: bool = False
    num_images: int = 0
    num_labels: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    storage_path: str  # Path in Cloud Storage
    metadata: Dict[str, Any] = {}
    
class Image(BaseFirestoreModel, BaseModel):
    """Image model"""
    model_config = {
        "from_attributes": True
    }
    
    dataset_id: str
    filename: str
    storage_path: str  # Path in Cloud Storage
    width: int
    height: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}
    
class Label(BaseFirestoreModel, BaseModel):
    """Label model for object detection"""
    model_config = {
        "from_attributes": True
    }
    
    image_id: str
    class_id: int
    x_center: float  # Normalized [0, 1]
    y_center: float  # Normalized [0, 1]
    width: float     # Normalized [0, 1]
    height: float    # Normalized [0, 1]
    confidence: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
