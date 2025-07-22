from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4


class FirestoreModel:
    """Base Firestore document model with common fields."""
    
    @staticmethod
    def timestamp_now():
        """Get current timestamp for Firestore."""
        return datetime.utcnow()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create model instance from Firestore document data."""
        instance = cls()
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for Firestore storage."""
        # Exclude non-serializable properties and methods
        return {
            key: value for key, value in self.__dict__.items() 
            if not key.startswith('_') and not callable(value)
        }


class Dataset(FirestoreModel):
    """Dataset model for Firestore."""
    
    def __init__(
        self, 
        name: str = None, 
        description: str = None, 
        storage_path: str = None,
        id: str = None,
        created_at: datetime = None,
        updated_at: datetime = None,
        status: str = "pending",
        import_progress: int = 0,
        error_message: str = None,
        image_count: int = 0,
        upload_id: str = None,
        size_bytes: int = 0
    ):
        self.id = id or str(uuid4())
        self.name = name
        self.description = description
        self.storage_path = storage_path or f"datasets/{self.id}"
        self.created_at = created_at or self.timestamp_now()
        self.updated_at = updated_at or self.timestamp_now()
        # Status can be: pending, importing, finalizing, ready, error
        self.status = status
        self.import_progress = import_progress
        self.error_message = error_message
        self.image_count = image_count
        self.upload_id = upload_id
        self.size_bytes = size_bytes


class Image(FirestoreModel):
    """Image model for Firestore."""
    
    def __init__(
        self,
        dataset_id: str = None,
        filename: str = None,
        storage_path: str = None,
        width: int = None,
        height: int = None,
        id: str = None,
        created_at: datetime = None,
        updated_at: datetime = None
    ):
        self.id = id or str(uuid4())
        self.dataset_id = dataset_id
        self.filename = filename
        self.width = width
        self.height = height
        self.storage_path = storage_path
        self.created_at = created_at or self.timestamp_now()
        self.updated_at = updated_at or self.timestamp_now()


class Label(FirestoreModel):
    """Label model for Firestore (YOLO format)."""
    
    def __init__(
        self,
        image_id: str = None,
        class_id: int = None,
        x_center: float = None,
        y_center: float = None,
        width: float = None,
        height: float = None,
        id: str = None,
        created_at: datetime = None,
        updated_at: datetime = None
    ):
        self.id = id or str(uuid4())
        self.image_id = image_id
        self.class_id = class_id
        self.x_center = x_center
        self.y_center = y_center
        self.width = width
        self.height = height
        self.created_at = created_at or self.timestamp_now()
        self.updated_at = updated_at or self.timestamp_now()


class ClassDefinition(FirestoreModel):
    """Class definition model for Firestore."""
    
    def __init__(
        self,
        class_id: int = None,
        name: str = None,
        description: str = None,
        id: str = None,
        created_at: datetime = None,
        updated_at: datetime = None
    ):
        self.id = id or str(uuid4())
        self.class_id = class_id
        self.name = name
        self.description = description
        self.created_at = created_at or self.timestamp_now()
        self.updated_at = updated_at or self.timestamp_now()
