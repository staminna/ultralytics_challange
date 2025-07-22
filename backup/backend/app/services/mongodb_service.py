"""
MongoDB Service for handling large datasets and optimizing performance.

This service provides MongoDB integration for storing and retrieving dataset information,
images, and labels. It's designed to work alongside Firestore for better performance
with large datasets (up to 100GB).
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pymongo import ASCENDING, DESCENDING, InsertOne, MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.errors import BulkWriteError

from ..core.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB collections
MONGO_COLLECTION_DATASETS = "datasets"
MONGO_COLLECTION_IMAGES = "images"
MONGO_COLLECTION_LABELS = "labels"
MONGO_COLLECTION_CLASSES = "class_definitions"
MONGO_COLLECTION_IMPORT_STATUS = "import_status"

class MongoDBService:
    """Service for MongoDB operations to handle large datasets."""
    
    def __init__(self):
        """Initialize MongoDB connection using settings."""
        self.settings = get_settings()
        self.mongo_uri = self.settings.mongodb_uri
        self.db_name = self.settings.mongodb_name
        self.client = None
        self.db = None
        self.connect()
        
    def connect(self) -> bool:
        """Connect to MongoDB server."""
        try:
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.server_info()
            self.db = self.client[self.db_name]
            
            # Create indexes for better performance
            self._create_indexes()
            
            logger.info(f"✅ Connected to MongoDB at {self.mongo_uri}")
            return True
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {str(e)}")
            self.client = None
            self.db = None
            return False
            
    def _create_indexes(self):
        """Create indexes for better query performance."""
        if not self.db:
            return
            
        # Dataset indexes
        self.db[MONGO_COLLECTION_DATASETS].create_index([("id", ASCENDING)], unique=True)
        self.db[MONGO_COLLECTION_DATASETS].create_index([("created_at", DESCENDING)])
        
        # Image indexes
        self.db[MONGO_COLLECTION_IMAGES].create_index([("id", ASCENDING)], unique=True)
        self.db[MONGO_COLLECTION_IMAGES].create_index([("dataset_id", ASCENDING)])
        self.db[MONGO_COLLECTION_IMAGES].create_index([("filename", ASCENDING)])
        
        # Label indexes
        self.db[MONGO_COLLECTION_LABELS].create_index([("id", ASCENDING)], unique=True)
        self.db[MONGO_COLLECTION_LABELS].create_index([("image_id", ASCENDING)])
        
        # Class definition indexes
        self.db[MONGO_COLLECTION_CLASSES].create_index([("dataset_id", ASCENDING), ("class_id", ASCENDING)], unique=True)
        
        # Import status indexes
        self.db[MONGO_COLLECTION_IMPORT_STATUS].create_index([("dataset_id", ASCENDING)], unique=True)
        
    def is_connected(self) -> bool:
        """Check if MongoDB is connected."""
        return self.client is not None and self.db is not None
        
    def store_dataset(self, dataset_data: Dict[str, Any]) -> bool:
        """Store dataset information in MongoDB."""
        if not self.is_connected():
            return False
            
        try:
            # Use upsert to update if exists or insert if not
            result = self.db[MONGO_COLLECTION_DATASETS].update_one(
                {"id": dataset_data["id"]},
                {"$set": dataset_data},
                upsert=True
            )
            return result.acknowledged
        except Exception as e:
            logger.error(f"❌ Failed to store dataset in MongoDB: {str(e)}")
            return False
            
    def store_images_batch(self, images: List[Dict[str, Any]]) -> Tuple[int, int]:
        """Store multiple images in MongoDB using bulk operations."""
        if not self.is_connected() or not images:
            return 0, 0
            
        try:
            # Prepare bulk operations
            operations = []
            for image in images:
                operations.append(
                    UpdateOne(
                        {"id": image["id"]},
                        {"$set": image},
                        upsert=True
                    )
                )
                
            if operations:
                result = self.db[MONGO_COLLECTION_IMAGES].bulk_write(operations)
                return result.upserted_count, result.modified_count
            return 0, 0
        except BulkWriteError as bwe:
            logger.error(f"❌ Bulk write error: {bwe.details}")
            return 0, 0
        except Exception as e:
            logger.error(f"❌ Failed to store images batch in MongoDB: {str(e)}")
            return 0, 0
            
    def store_labels_batch(self, labels: List[Dict[str, Any]]) -> Tuple[int, int]:
        """Store multiple labels in MongoDB using bulk operations."""
        if not self.is_connected() or not labels:
            return 0, 0
            
        try:
            # Prepare bulk operations
            operations = []
            for label in labels:
                operations.append(
                    UpdateOne(
                        {"id": label["id"]},
                        {"$set": label},
                        upsert=True
                    )
                )
                
            if operations:
                result = self.db[MONGO_COLLECTION_LABELS].bulk_write(operations)
                return result.upserted_count, result.modified_count
            return 0, 0
        except BulkWriteError as bwe:
            logger.error(f"❌ Bulk write error: {bwe.details}")
            return 0, 0
        except Exception as e:
            logger.error(f"❌ Failed to store labels batch in MongoDB: {str(e)}")
            return 0, 0
            
    def store_class_definitions(self, dataset_id: str, class_definitions: List[Dict[str, Any]]) -> bool:
        """Store class definitions for a dataset."""
        if not self.is_connected():
            return False
            
        try:
            # Delete existing class definitions for this dataset
            self.db[MONGO_COLLECTION_CLASSES].delete_many({"dataset_id": dataset_id})
            
            # Insert new class definitions
            if class_definitions:
                self.db[MONGO_COLLECTION_CLASSES].insert_many(class_definitions)
            return True
        except Exception as e:
            logger.error(f"❌ Failed to store class definitions in MongoDB: {str(e)}")
            return False
            
    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Get dataset by ID from MongoDB."""
        if not self.is_connected():
            return None
            
        try:
            return self.db[MONGO_COLLECTION_DATASETS].find_one({"id": dataset_id}, {"_id": 0})
        except Exception as e:
            logger.error(f"❌ Failed to get dataset from MongoDB: {str(e)}")
            return None
            
    def list_datasets(self, limit: int = 100, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """List datasets with pagination from MongoDB."""
        if not self.is_connected():
            return [], 0
            
        try:
            # Get total count
            total = self.db[MONGO_COLLECTION_DATASETS].count_documents({})
            
            # Get datasets with pagination
            cursor = self.db[MONGO_COLLECTION_DATASETS].find(
                {},
                {"_id": 0}
            ).sort("created_at", DESCENDING).skip(offset).limit(limit)
            
            datasets = list(cursor)
            
            # Add image count for each dataset
            for dataset in datasets:
                dataset_id = dataset.get("id")
                if dataset_id:
                    image_count = self.db[MONGO_COLLECTION_IMAGES].count_documents({"dataset_id": dataset_id})
                    dataset["image_count"] = image_count
                    
            return datasets, total
        except Exception as e:
            logger.error(f"❌ Failed to list datasets from MongoDB: {str(e)}")
            return [], 0
            
    def get_images_for_dataset(
        self, dataset_id: str, limit: int = 100, offset: int = 0, with_labels: bool = True
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get images with optional labels for a dataset."""
        if not self.is_connected():
            return [], 0
            
        try:
            # Get total count
            total = self.db[MONGO_COLLECTION_IMAGES].count_documents({"dataset_id": dataset_id})
            
            # Get images with pagination
            cursor = self.db[MONGO_COLLECTION_IMAGES].find(
                {"dataset_id": dataset_id},
                {"_id": 0}
            ).sort("created_at", ASCENDING).skip(offset).limit(limit)
            
            images = list(cursor)
            
            # Add labels if requested
            if with_labels:
                for image in images:
                    image_id = image.get("id")
                    if image_id:
                        labels = list(self.db[MONGO_COLLECTION_LABELS].find(
                            {"image_id": image_id},
                            {"_id": 0}
                        ))
                        image["labels"] = labels
                        
            return images, total
        except Exception as e:
            logger.error(f"❌ Failed to get images from MongoDB: {str(e)}")
            return [], 0
            
    def get_class_definitions(self, dataset_id: str) -> List[Dict[str, Any]]:
        """Get class definitions for a dataset."""
        if not self.is_connected():
            return []
            
        try:
            return list(self.db[MONGO_COLLECTION_CLASSES].find(
                {"dataset_id": dataset_id},
                {"_id": 0}
            ).sort("class_id", ASCENDING))
        except Exception as e:
            logger.error(f"❌ Failed to get class definitions from MongoDB: {str(e)}")
            return []
            
    def update_import_status(self, dataset_id: str, status: str, progress: float = 0.0, 
                           message: str = "", error: str = "") -> bool:
        """Update import status for a dataset."""
        if not self.is_connected():
            return False
            
        try:
            self.db[MONGO_COLLECTION_IMPORT_STATUS].update_one(
                {"dataset_id": dataset_id},
                {"$set": {
                    "dataset_id": dataset_id,
                    "status": status,
                    "progress": progress,
                    "message": message,
                    "error": error,
                    "updated_at": datetime.now().isoformat()
                }},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update import status in MongoDB: {str(e)}")
            return False
            
    def get_import_status(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Get import status for a dataset."""
        if not self.is_connected():
            return None
            
        try:
            return self.db[MONGO_COLLECTION_IMPORT_STATUS].find_one(
                {"dataset_id": dataset_id},
                {"_id": 0}
            )
        except Exception as e:
            logger.error(f"❌ Failed to get import status from MongoDB: {str(e)}")
            return None
