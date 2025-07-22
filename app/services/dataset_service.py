import io
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from google.cloud import firestore, storage
from google.cloud.exceptions import NotFound

from app.core.config import settings
from app.models.firestore_models import Dataset, Image, Label

# Firestore collection names
DATASET_COLLECTION = "datasets"
IMAGE_COLLECTION = "images"
LABEL_COLLECTION = "labels"

class DatasetService:
    def __init__(self):
        """Initialize the dataset service with Firestore and Cloud Storage clients."""
        self.db = firestore.Client()
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(settings.STORAGE_BUCKET)
    
    # Dataset operations
    async def create_dataset(self, dataset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new dataset"""
        try:
            # Add timestamps
            now = datetime.utcnow()
            dataset_data.update({
                "created_at": now,
                "updated_at": now
            })
            
            # Check if dataset with same name already exists
            existing = (
                self.db.collection(DATASET_COLLECTION)
                .where("name", "==", dataset_data["name"])
                .limit(1)
                .stream()
            )
            
            if list(existing):
                raise ValueError(f"Dataset with name '{dataset_data['name']}' already exists")
            
            # Create storage path
            storage_path = f"datasets/{dataset_data['name'].lower().replace(' ', '_')}"
            dataset_data["storage_path"] = storage_path
            
            # Create in Firestore
            doc_ref = self.db.collection(DATASET_COLLECTION).document()
            doc_ref.set(dataset_data)
            
            # Return the created dataset with ID
            return {
                "id": doc_ref.id,
                **dataset_data
            }
            
        except Exception as e:
            logger.error(f"Error creating dataset: {str(e)}")
            raise
    
    async def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """Get a dataset by ID."""
        doc_ref = self.db.collection(DATASET_COLLECTION).document(dataset_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return None
            
        return Dataset.from_dict({"id": doc.id, **doc.to_dict()})
    
    async def list_datasets(self, skip: int = 0, limit: int = 100) -> Tuple[List[Dict[str, Any]], int]:
        """List all datasets with pagination."""
        query = self.db.collection(DATASET_COLLECTION)
        
        # Get total count
        total = len([_ for _ in query.stream()])
        
        # Apply pagination
        datasets = []
        for doc in query.offset(skip).limit(limit).stream():
            datasets.append({"id": doc.id, **doc.to_dict()})
            
        return datasets, total
    
    # Image operations
    async def get_images_for_dataset(
        self, dataset_id: str, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get all images for a dataset with pagination."""
        # Get dataset to verify it exists
        dataset = await self.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        # Query images
        images_ref = self.db.collection(IMAGE_COLLECTION)
        query = images_ref.where("dataset_id", "==", dataset_id)
        
        # Get total count
        total = len([_ for _ in query.stream()])
        
        # Apply pagination
        images = []
        for doc in query.offset(skip).limit(limit).stream():
            image_data = {"id": doc.id, **doc.to_dict()}
            
            # Generate signed URL for image download
            blob = self.bucket.blob(image_data["storage_path"])
            image_data["download_url"] = blob.generate_signed_url(
                version="v4",
                expiration=3600,  # 1 hour
                method="GET"
            )
            
            # Get labels for this image
            labels_ref = self.db.collection(LABEL_COLLECTION)
            labels_query = labels_ref.where("image_id", "==", doc.id)
            labels = [{"id": label.id, **label.to_dict()} for label in labels_query.stream()]
            
            image_data["labels"] = labels
            images.append(image_data)
            
        return images, total
    
    async def import_yolo_dataset(
        self, zip_file: bytes, dataset_name: str, description: Optional[str] = None
    ) -> Dataset:
        """Import a YOLO format dataset from a ZIP file."""
        # Create a temporary directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_zip = os.path.join(temp_dir, "dataset.zip")
            
            # Save uploaded file
            with open(temp_zip, "wb") as f:
                f.write(zip_file)
            
            # Extract ZIP file
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Process the extracted files
            return await self._process_yolo_dataset(extract_dir, dataset_name, description)
    
    async def _process_yolo_dataset(
        self, dataset_dir: str, dataset_name: str, description: Optional[str] = None
    ) -> Dataset:
        """Process a YOLO format dataset from an extracted directory."""
        # Implementation for processing YOLO dataset
        # This is a simplified version - you'll need to implement the actual processing
        
        # Create dataset
        dataset = await self.create_dataset({
            "name": dataset_name,
            "description": description,
            "num_images": 0,
            "num_classes": 0,
            "storage_path": f"datasets/{dataset_name.lower().replace(' ', '_')}"
        })
        
        # TODO: Implement actual YOLO dataset processing
        # This would involve:
        # 1. Finding images and labels
        # 2. Uploading images to Cloud Storage
        # 3. Creating Image and Label documents in Firestore
        # 4. Updating the dataset with counts
        
        return dataset

# Singleton instance
dataset_service = DatasetService()
