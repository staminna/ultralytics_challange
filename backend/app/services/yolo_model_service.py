"""
YOLOv8-X Model Service for Dataset Annotation.

This service provides methods to use the YOLOv8-X model for:
1. Inference on uploaded images
2. Auto-annotation of datasets
3. Model fine-tuning on custom datasets
"""

import io
import os
import tempfile
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple

import numpy as np
import torch
from fastapi import BackgroundTasks, HTTPException, UploadFile
from PIL import Image as PILImage
from ultralytics import YOLO

from ..core.config import get_settings
from ..core.gcp import get_firestore_client, get_storage_bucket
from ..models.firestore_models import ClassDefinition, Dataset, Image, Label

# Get settings
settings = get_settings()

# Default COCO classes for YOLOv8
COCO_CLASSES = [
    'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
    'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat',
    'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'backpack',
    'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
    'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
    'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
    'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair',
    'couch', 'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
    'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator',
    'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
]

class YOLOModelService:
    """Service for working with YOLOv11 model."""
    
    def __init__(self):
        """Initialize the YOLO model service."""
        self.db = get_firestore_client()
        self.bucket = get_storage_bucket()
        self.settings = get_settings()
        self.model = None
        self.model_path = Path(os.getenv("YOLO11_MODEL_PATH", "yolo11x.pt"))
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Firestore collections
        self.DATASET_COLLECTION = "datasets"
        self.CLASS_COLLECTION = "class_definitions"
        self.MODEL_COLLECTION = "models"
        
    async def load_model(self) -> None:
        """Load YOLO11 model."""
        try:
            print(f"Loading YOLO11 model on {self.device}...")
            
            # Download model if not available locally
            if not os.path.exists(self.model_path):
                print(f"Downloading YOLO11 model...")
                self.model = YOLO("yolo11x.pt")  # This will download the model automatically
                # Save model to the specified path
                self.model_path.parent.mkdir(parents=True, exist_ok=True)
                self.model.save(str(self.model_path))
            else:
                self.model = YOLO(self.model_path)
                
            print(f"YOLOv11 model loaded successfully")
            return self.model
        except Exception as e:
            print(f"Error loading YOLOv11 model: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load YOLOv11 model: {str(e)}"
            )
    
    async def predict(self, image_data: bytes, confidence: float = 0.25) -> List[Dict[str, Any]]:
        """
        Run prediction on an image using YOLOv11.
        
        Args:
            image_data: The image bytes to run prediction on
            confidence: Confidence threshold for detections
            
        Returns:
            List of detected objects with bounding boxes and classes
        """
        if self.model is None:
            await self.load_model()
        
        try:
            # Process image
            image = PILImage.open(io.BytesIO(image_data))
            
            # Run prediction
            results = self.model.predict(image, conf=confidence)
            
            # Process results
            detections = []
            for result in results:
                boxes = result.boxes
                
                for i, box in enumerate(boxes):
                    # Extract information
                    x1, y1, x2, y2 = box.xyxy[0].tolist()  # box coordinates
                    conf = box.conf.item()  # confidence score
                    cls_id = int(box.cls.item())  # class id
                    
                    # Convert to YOLO format (normalized coordinates)
                    img_width, img_height = image.size
                    x_center = (x1 + x2) / 2 / img_width
                    y_center = (y1 + y2) / 2 / img_height
                    width = (x2 - x1) / img_width
                    height = (y2 - y1) / img_height
                    
                    # Create detection object
                    detection = {
                        "class_id": cls_id,
                        "class_name": COCO_CLASSES[cls_id] if cls_id < len(COCO_CLASSES) else f"class_{cls_id}",
                        "confidence": conf,
                        "x_center": x_center,
                        "y_center": y_center,
                        "width": width,
                        "height": height,
                        # Also include absolute coordinates for display
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2
                    }
                    detections.append(detection)
            
            return detections
            
        except Exception as e:
            print(f"Error running prediction: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to run prediction: {str(e)}"
            )
    
    async def auto_annotate_image(
        self, 
        image_id: str, 
        confidence: float = 0.25,
        class_filter: List[int] = None
    ) -> List[Label]:
        """
        Auto-annotate an image using YOLOv8-X.
        
        Args:
            image_id: ID of the image to annotate
            confidence: Confidence threshold for detections
            class_filter: Optional list of class IDs to include
            
        Returns:
            List of created label objects
        """
        # Get image from Firestore
        image_ref = self.db.collection("images").document(image_id)
        image_doc = image_ref.get()
        
        if not image_doc.exists:
            raise HTTPException(status_code=404, detail=f"Image not found: {image_id}")
        
        image_data = image_doc.to_dict()
        
        # Get image content from Cloud Storage
        storage_path = image_data.get("storage_path")
        if not storage_path:
            raise HTTPException(
                status_code=400, 
                detail=f"Image {image_id} has no storage path"
            )
        
        # Download image
        blob = self.bucket.blob(storage_path)
        image_bytes = blob.download_as_bytes()
        
        # Run prediction
        detections = await self.predict(image_bytes, confidence)
        
        # Filter by class if requested
        if class_filter:
            detections = [d for d in detections if d["class_id"] in class_filter]
        
        # Create labels
        created_labels = []
        for detection in detections:
            label_data = {
                "class_id": detection["class_id"],
                "x_center": detection["x_center"],
                "y_center": detection["y_center"],
                "width": detection["width"],
                "height": detection["height"]
            }
            
            # Create label
            label = Label(
                image_id=image_id,
                class_id=label_data["class_id"],
                x_center=label_data["x_center"],
                y_center=label_data["y_center"],
                width=label_data["width"],
                height=label_data["height"]
            )
            
            # Save to Firestore
            label_ref = self.db.collection("labels").document(label.id)
            label_ref.set(label.to_dict())
            created_labels.append(label)
        
        return created_labels
    
    async def auto_annotate_dataset(
        self, 
        dataset_id: str,
        background_tasks: BackgroundTasks,
        confidence: float = 0.25,
        class_filter: List[int] = None
    ) -> Dict[str, Any]:
        """
        Auto-annotate an entire dataset using YOLOv8-X.
        
        Args:
            dataset_id: ID of the dataset to annotate
            background_tasks: FastAPI background tasks object for async processing
            confidence: Confidence threshold for detections
            class_filter: Optional list of class IDs to include
            
        Returns:
            Dictionary with job status information
        """
        # Check if dataset exists
        dataset_ref = self.db.collection(self.DATASET_COLLECTION).document(dataset_id)
        dataset_doc = dataset_ref.get()
        
        if not dataset_doc.exists:
            raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")
        
        # Update dataset status
        dataset_ref.update({
            "status": "annotating",
            "annotation_progress": 0
        })
        
        # Add background task
        background_tasks.add_task(
            self._background_auto_annotate,
            dataset_id=dataset_id,
            confidence=confidence,
            class_filter=class_filter
        )
        
        return {
            "status": "started",
            "dataset_id": dataset_id,
            "message": "Auto-annotation started in background"
        }
    
    async def _background_auto_annotate(
        self, 
        dataset_id: str, 
        confidence: float = 0.25,
        class_filter: List[int] = None
    ) -> None:
        """
        Background task to auto-annotate a dataset.
        
        Args:
            dataset_id: ID of the dataset to annotate
            confidence: Confidence threshold for detections
            class_filter: Optional list of class IDs to include
        """
        try:
            # Load model if not already loaded
            if self.model is None:
                await self.load_model()
                
            # Get images in dataset
            images_query = self.db.collection("images").where("dataset_id", "==", dataset_id)
            image_docs = list(images_query.stream())
            total_images = len(image_docs)
            
            print(f"Starting auto-annotation of {total_images} images in dataset {dataset_id}")
            
            # Process each image
            for i, image_doc in enumerate(image_docs):
                try:
                    image_id = image_doc.id
                    print(f"Auto-annotating image {i+1}/{total_images}: {image_id}")
                    
                    # Auto-annotate image
                    await self.auto_annotate_image(
                        image_id=image_id,
                        confidence=confidence,
                        class_filter=class_filter
                    )
                    
                    # Update progress
                    progress = int((i + 1) / total_images * 100)
                    dataset_ref = self.db.collection(self.DATASET_COLLECTION).document(dataset_id)
                    dataset_ref.update({
                        "annotation_progress": progress
                    })
                    
                except Exception as img_error:
                    print(f"Error annotating image {image_doc.id}: {str(img_error)}")
                    # Continue with next image
            
            # Update dataset status
            dataset_ref = self.db.collection(self.DATASET_COLLECTION).document(dataset_id)
            dataset_ref.update({
                "status": "ready",
                "annotation_progress": 100
            })
            
            print(f"Auto-annotation of dataset {dataset_id} completed")
            
        except Exception as e:
            print(f"Error in background auto-annotation: {str(e)}")
            # Update dataset status
            dataset_ref = self.db.collection(self.DATASET_COLLECTION).document(dataset_id)
            dataset_ref.update({
                "status": "error",
                "error_message": f"Auto-annotation failed: {str(e)}"
            })
    
    async def fine_tune_model(
        self,
        dataset_id: str,
        background_tasks: BackgroundTasks,
        epochs: int = 10,
        batch_size: int = 16,
        model_name: str = "custom_model"
    ) -> Dict[str, Any]:
        """
        Fine-tune YOLOv8-X model on a custom dataset.
        
        Args:
            dataset_id: ID of the dataset to use for fine-tuning
            epochs: Number of training epochs
            batch_size: Training batch size
            background_tasks: FastAPI background tasks object
            model_name: Name for the fine-tuned model
            
        Returns:
            Dictionary with job status information
        """
        # Check if dataset exists
        dataset_ref = self.db.collection(self.DATASET_COLLECTION).document(dataset_id)
        dataset_doc = dataset_ref.get()
        
        if not dataset_doc.exists:
            raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")
        
        # Update dataset status
        dataset_ref.update({
            "status": "training",
            "training_progress": 0
        })
        
        # Create a model record
        model_id = f"{dataset_id}_{model_name}"
        model_ref = self.db.collection(self.MODEL_COLLECTION).document(model_id)
        model_ref.set({
            "id": model_id,
            "name": model_name,
            "dataset_id": dataset_id,
            "status": "training",
            "created_at": Dataset.timestamp_now(),
            "updated_at": Dataset.timestamp_now()
        })
        
        # Add background task
        background_tasks.add_task(
            self._background_fine_tune,
            dataset_id=dataset_id,
            epochs=epochs,
            batch_size=batch_size,
            model_id=model_id
        )
        
        return {
            "status": "started",
            "model_id": model_id,
            "dataset_id": dataset_id,
            "message": "Model fine-tuning started in background"
        }
    
    async def _background_fine_tune(
        self, 
        dataset_id: str,
        epochs: int,
        batch_size: int,
        model_id: str
    ) -> None:
        """
        Background task to fine-tune a YOLOv8 model.
        
        Args:
            dataset_id: ID of the dataset to use
            epochs: Number of training epochs
            batch_size: Training batch size
            model_id: ID of the model record
        """
        temp_dir = None
        try:
            # Create temporary directory for dataset
            temp_dir = tempfile.mkdtemp()
            dataset_dir = os.path.join(temp_dir, "dataset")
            os.makedirs(dataset_dir, exist_ok=True)
            
            # Prepare dataset in YOLO format
            await self._prepare_dataset_for_training(dataset_id, dataset_dir)
            
            # Load base model
            if self.model is None:
                await self.load_model()
            
            # Start fine-tuning
            print(f"Starting fine-tuning on dataset {dataset_id} for {epochs} epochs")
            
            # Create data.yaml file
            class_names = await self._get_class_names_for_dataset(dataset_id)
            yaml_path = os.path.join(dataset_dir, "data.yaml")
            with open(yaml_path, "w") as f:
                f.write(f"train: {os.path.join(dataset_dir, 'train', 'images')}\n")
                f.write(f"val: {os.path.join(dataset_dir, 'val', 'images')}\n")
                f.write(f"nc: {len(class_names)}\n")
                f.write(f"names: {class_names}\n")
            
            # Train the model
            results = self.model.train(
                data=yaml_path,
                epochs=epochs,
                batch=batch_size,
                imgsz=640,
                project=os.path.join(temp_dir, "runs"),
                name=model_id
            )
            
            # Upload trained model to Cloud Storage
            best_model_path = os.path.join(temp_dir, "runs", model_id, "weights", "best.pt")
            model_storage_path = f"models/{model_id}/best.pt"
            
            blob = self.bucket.blob(model_storage_path)
            blob.upload_from_filename(best_model_path)
            
            # Update model record
            model_ref = self.db.collection(self.MODEL_COLLECTION).document(model_id)
            model_ref.update({
                "status": "ready",
                "storage_path": model_storage_path,
                "metrics": results,
                "updated_at": Dataset.timestamp_now()
            })
            
            # Update dataset status
            dataset_ref = self.db.collection(self.DATASET_COLLECTION).document(dataset_id)
            dataset_ref.update({
                "status": "ready",
                "training_progress": 100
            })
            
            print(f"Fine-tuning of model {model_id} completed")
            
        except Exception as e:
            print(f"Error in background fine-tuning: {str(e)}")
            # Update model status
            model_ref = self.db.collection(self.MODEL_COLLECTION).document(model_id)
            model_ref.update({
                "status": "error",
                "error_message": f"Fine-tuning failed: {str(e)}",
                "updated_at": Dataset.timestamp_now()
            })
            
            # Update dataset status
            dataset_ref = self.db.collection(self.DATASET_COLLECTION).document(dataset_id)
            dataset_ref.update({
                "status": "error",
                "error_message": f"Model training failed: {str(e)}"
            })
        finally:
            # Cleanup temporary files
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def _prepare_dataset_for_training(self, dataset_id: str, output_dir: str) -> None:
        """
        Prepare dataset in YOLO format for training.
        
        Args:
            dataset_id: ID of the dataset
            output_dir: Directory to output the prepared dataset
        """
        # Create directory structure
        train_img_dir = os.path.join(output_dir, "train", "images")
        train_lbl_dir = os.path.join(output_dir, "train", "labels")
        val_img_dir = os.path.join(output_dir, "val", "images")
        val_lbl_dir = os.path.join(output_dir, "val", "labels")
        
        os.makedirs(train_img_dir, exist_ok=True)
        os.makedirs(train_lbl_dir, exist_ok=True)
        os.makedirs(val_img_dir, exist_ok=True)
        os.makedirs(val_lbl_dir, exist_ok=True)
        
        # Get images in dataset
        images_query = self.db.collection("images").where("dataset_id", "==", dataset_id)
        image_docs = list(images_query.stream())
        
        # Split into train/val (80/20)
        np.random.shuffle(image_docs)
        split_idx = int(len(image_docs) * 0.8)
        train_images = image_docs[:split_idx]
        val_images = image_docs[split_idx:]
        
        # Process training images
        await self._process_images_for_training(train_images, train_img_dir, train_lbl_dir)
        
        # Process validation images
        await self._process_images_for_training(val_images, val_img_dir, val_lbl_dir)
    
    async def _process_images_for_training(self, image_docs, img_dir, lbl_dir) -> None:
        """
        Process images and labels for training.
        
        Args:
            image_docs: List of Firestore image documents
            img_dir: Directory to save images
            lbl_dir: Directory to save labels
        """
        for image_doc in image_docs:
            image_data = image_doc.to_dict()
            image_id = image_doc.id
            
            # Download image from Cloud Storage
            storage_path = image_data.get("storage_path")
            filename = image_data.get("filename")
            
            if not storage_path or not filename:
                print(f"Skipping image {image_id}: missing storage path or filename")
                continue
            
            # Download image
            blob = self.bucket.blob(storage_path)
            image_path = os.path.join(img_dir, filename)
            blob.download_to_filename(image_path)
            
            # Get labels for this image
            labels_query = self.db.collection("labels").where("image_id", "==", image_id)
            label_docs = list(labels_query.stream())
            
            # Create YOLO format label file
            label_path = os.path.join(lbl_dir, os.path.splitext(filename)[0] + ".txt")
            with open(label_path, "w") as f:
                for label_doc in label_docs:
                    label_data = label_doc.to_dict()
                    # YOLO format: class_id x_center y_center width height
                    line = (f"{label_data.get('class_id')} "
                            f"{label_data.get('x_center')} "
                            f"{label_data.get('y_center')} "
                            f"{label_data.get('width')} "
                            f"{label_data.get('height')}\n")
                    f.write(line)
    
    async def _get_class_names_for_dataset(self, dataset_id: str) -> List[str]:
        """Get class names associated with a dataset."""
        class_query = self.db.collection(self.CLASS_COLLECTION).where("dataset_id", "==", dataset_id)
        class_docs = list(class_query.stream())
        
        # Sort by class_id
        class_defs = [ClassDefinition.from_dict(doc.to_dict()) for doc in class_docs]
        class_defs.sort(key=lambda x: x.class_id)
        
        # Get class names
        class_names = [cls.name for cls in class_defs]
        
        # If no classes found, return a default list
        if not class_names:
            return ["unknown"]
        
        return class_names
