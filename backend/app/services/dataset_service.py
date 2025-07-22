import os
import io
from typing import List, Dict, Any, Tuple, Optional
from fastapi import UploadFile, HTTPException
from PIL import Image as PILImage
from datetime import datetime, timedelta

from ..core.gcp import get_firestore_client, get_storage_bucket
from ..models.firestore_models import Dataset, Image, Label, ClassDefinition
from ..schemas.dataset import DatasetCreate, ImageCreate, LabelCreate

# Collections in Firestore
DATASET_COLLECTION = "datasets"
IMAGE_COLLECTION = "images"
LABEL_COLLECTION = "labels"
CLASS_COLLECTION = "class_definitions"


class DatasetService:
    """Service for managing datasets in Firestore and Cloud Storage."""
    
    def __init__(self):
        self.db = get_firestore_client()
        self.bucket = get_storage_bucket()
    
    async def create_dataset(self, dataset_data: DatasetCreate) -> Dataset:
        """Create a new dataset."""
        dataset = Dataset(
            name=dataset_data.name,
            description=dataset_data.description
        )
        
        # Save to Firestore
        dataset_ref = self.db.collection(DATASET_COLLECTION).document(dataset.id)
        dataset_ref.set(dataset.to_dict())
        
        return dataset
    
    async def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """Get a dataset by ID."""
        dataset_ref = self.db.collection(DATASET_COLLECTION).document(dataset_id)
        dataset_doc = dataset_ref.get()
        
        if not dataset_doc.exists:
            return None
            
        return Dataset.from_dict(dataset_doc.to_dict())
    
    async def list_datasets(self, limit: int = 100, offset: int = 0) -> Tuple[List[Dataset], int]:
        """List datasets with pagination."""
        query = self.db.collection(DATASET_COLLECTION).order_by("created_at", direction="DESCENDING")
        
        # Get total count (this is not efficient for large collections but works for demo)
        total_query = query.stream()
        total = sum(1 for _ in total_query)
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        dataset_docs = query.stream()
        
        datasets = []
        for doc in dataset_docs:
            dataset = Dataset.from_dict(doc.to_dict())
            
            # Count images for each dataset
            images_query = self.db.collection(IMAGE_COLLECTION).where("dataset_id", "==", dataset.id)
            image_count = len(list(images_query.stream()))
            dataset.image_count = image_count
            
            datasets.append(dataset)
            
        return datasets, total
    
    async def get_images_for_dataset(
        self, dataset_id: str, limit: int = 100, offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get images with their labels for a specific dataset."""
        # Verify dataset exists
        dataset = await self.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Query images
        images_query = (
            self.db.collection(IMAGE_COLLECTION)
            .where("dataset_id", "==", dataset_id)
            .order_by("created_at")
        )
        
        # Get total count
        total_query = images_query.stream()
        total = sum(1 for _ in total_query)
        
        # Apply pagination
        images_query = images_query.offset(offset).limit(limit)
        image_docs = list(images_query.stream())
        
        images_with_labels = []
        for img_doc in image_docs:
            image_data = img_doc.to_dict()
            image_id = img_doc.id
            
            # Get labels for this image
            labels_query = self.db.collection(LABEL_COLLECTION).where("image_id", "==", image_id)
            label_docs = labels_query.stream()
            
            labels = [Label.from_dict(doc.to_dict()) for doc in label_docs]
            
            # Generate signed URL for image download
            blob = self.bucket.blob(image_data["storage_path"])
            download_url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=30),
                method="GET"
            )
            
            image_data["labels"] = [label.to_dict() for label in labels]
            image_data["download_url"] = download_url
            
            images_with_labels.append(image_data)
            
        return images_with_labels, total
    
    async def upload_image_to_dataset(
        self, dataset_id: str, file: UploadFile, width: int = None, height: int = None
    ) -> Image:
        """Upload a single image to a dataset."""
        # Verify dataset exists
        dataset = await self.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Read image file
        file_content = await file.read()
        
        # Validate image
        try:
            with PILImage.open(io.BytesIO(file_content)) as img:
                if not width or not height:
                    width, height = img.size
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")
        
        # Create image record
        image = Image(
            dataset_id=dataset_id,
            filename=file.filename,
            storage_path=f"datasets/{dataset_id}/images/{file.filename}",
            width=width,
            height=height
        )
        
        # Upload to Cloud Storage
        blob = self.bucket.blob(image.storage_path)
        blob.upload_from_string(file_content, content_type=file.content_type)
        
        # Save to Firestore
        image_ref = self.db.collection(IMAGE_COLLECTION).document(image.id)
        image_ref.set(image.to_dict())
        
        return image
    
    async def create_label(self, image_id: str, label_data: LabelCreate) -> Label:
        """Create a label for an image."""
        # Verify image exists
        image_ref = self.db.collection(IMAGE_COLLECTION).document(image_id)
        image_doc = image_ref.get()
        
        if not image_doc.exists:
            raise HTTPException(status_code=404, detail="Image not found")
            
        # Create label
        label = Label(
            image_id=image_id,
            class_id=label_data.class_id,
            x_center=label_data.x_center,
            y_center=label_data.y_center,
            width=label_data.width,
            height=label_data.height
        )
        
        # Save to Firestore
        label_ref = self.db.collection(LABEL_COLLECTION).document(label.id)
        label_ref.set(label.to_dict())
        
        return label
    
    async def get_image(self, image_id: str) -> Optional[Image]:
        """Get an image by ID."""
        image_ref = self.db.collection(IMAGE_COLLECTION).document(image_id)
        image_doc = image_ref.get()
        
        if not image_doc.exists:
            return None
            
        image_data = image_doc.to_dict()
        
        # Generate signed URL for image download
        blob = self.bucket.blob(image_data["storage_path"])
        download_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=30),
            method="GET"
        )
        
        # Get labels for this image
        labels_query = self.db.collection(LABEL_COLLECTION).where("image_id", "==", image_id)
        label_docs = labels_query.stream()
        labels = [Label.from_dict(doc.to_dict()) for doc in label_docs]
        
        image = Image.from_dict(image_data)
        image_dict = image.to_dict()
        image_dict["download_url"] = download_url
        image_dict["labels"] = [label.to_dict() for label in labels]
        
        return image_dict
    
    async def update_image(self, image_id: str, filename: str = None, width: int = None, height: int = None) -> Optional[Image]:
        """Update image metadata."""
        image_ref = self.db.collection(IMAGE_COLLECTION).document(image_id)
        image_doc = image_ref.get()
        
        if not image_doc.exists:
            return None
        
        update_data = {"updated_at": datetime.utcnow()}
        
        if filename is not None:
            update_data["filename"] = filename
        if width is not None:
            update_data["width"] = width
        if height is not None:
            update_data["height"] = height
            
        image_ref.update(update_data)
        
        # Return updated image
        updated_doc = image_ref.get()
        return Image.from_dict(updated_doc.to_dict())
    
    async def delete_image(self, image_id: str) -> bool:
        """Delete an image and all its labels."""
        image_ref = self.db.collection(IMAGE_COLLECTION).document(image_id)
        image_doc = image_ref.get()
        
        if not image_doc.exists:
            return False
        
        image_data = image_doc.to_dict()
        
        # Delete from Cloud Storage
        try:
            blob = self.bucket.blob(image_data["storage_path"])
            blob.delete()
        except Exception as e:
            print(f"Warning: Could not delete image from storage: {e}")
        
        # Delete all labels for this image
        labels_query = self.db.collection(LABEL_COLLECTION).where("image_id", "==", image_id)
        label_docs = labels_query.stream()
        
        for label_doc in label_docs:
            label_doc.reference.delete()
        
        # Delete image document
        image_ref.delete()
        
        return True
    
    async def delete_dataset(self, dataset_id: str) -> bool:
        """Delete a dataset and all its images and labels."""
        dataset_ref = self.db.collection(DATASET_COLLECTION).document(dataset_id)
        dataset_doc = dataset_ref.get()
        
        if not dataset_doc.exists:
            return False
        
        # Get all images in the dataset
        images_query = self.db.collection(IMAGE_COLLECTION).where("dataset_id", "==", dataset_id)
        image_docs = images_query.stream()
        
        # Delete each image (this will also delete their labels)
        for image_doc in image_docs:
            await self.delete_image(image_doc.id)
        
        # Delete class definitions for this dataset
        classes_query = self.db.collection(CLASS_COLLECTION).where("dataset_id", "==", dataset_id)
        class_docs = classes_query.stream()
        
        for class_doc in class_docs:
            class_doc.reference.delete()
        
        # Delete dataset folder from Cloud Storage
        dataset_data = dataset_doc.to_dict()
        storage_path = dataset_data.get("storage_path", f"datasets/{dataset_id}")
        
        try:
            # List and delete all blobs in the dataset folder
            blobs = self.bucket.list_blobs(prefix=storage_path)
            for blob in blobs:
                blob.delete()
        except Exception as e:
            print(f"Warning: Could not delete dataset folder from storage: {e}")
        
        # Delete dataset document
        dataset_ref.delete()
        
        return True
    
    async def get_label(self, label_id: str) -> Optional[Label]:
        """Get a label by ID."""
        label_ref = self.db.collection(LABEL_COLLECTION).document(label_id)
        label_doc = label_ref.get()
        
        if not label_doc.exists:
            return None
            
        return Label.from_dict(label_doc.to_dict())
    
    async def update_label(self, label_id: str, class_id: int = None, x_center: float = None, 
                          y_center: float = None, width: float = None, height: float = None) -> Optional[Label]:
        """Update a label."""
        label_ref = self.db.collection(LABEL_COLLECTION).document(label_id)
        label_doc = label_ref.get()
        
        if not label_doc.exists:
            return None
        
        update_data = {"updated_at": datetime.utcnow()}
        
        if class_id is not None:
            update_data["class_id"] = class_id
        if x_center is not None:
            update_data["x_center"] = x_center
        if y_center is not None:
            update_data["y_center"] = y_center
        if width is not None:
            update_data["width"] = width
        if height is not None:
            update_data["height"] = height
            
        label_ref.update(update_data)
        
        # Return updated label
        updated_doc = label_ref.get()
        return Label.from_dict(updated_doc.to_dict())
    
    async def delete_label(self, label_id: str) -> bool:
        """Delete a label."""
        label_ref = self.db.collection(LABEL_COLLECTION).document(label_id)
        label_doc = label_ref.get()
        
        if not label_doc.exists:
            return False
        
        label_ref.delete()
        return True
