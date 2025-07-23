import asyncio
import io
import logging
import os
import shutil
import tempfile
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from typing import Any, BinaryIO, Dict, List, Optional, Set, Tuple

import yaml
from fastapi import BackgroundTasks, HTTPException, UploadFile
from PIL import Image as PILImage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from ..core.config import get_settings
from ..core.gcp import get_firestore_client, get_storage_bucket
from ..models.firestore_models import ClassDefinition, Dataset, Image, Label
from ..schemas.dataset import DatasetCreate, LabelCreate
from .chunked_upload_service import ChunkedUploadService
from .dataset_service import DatasetService
from .mongodb_service import MongoDBService


class YoloImportService:
    """Service for importing YOLO format datasets."""
    
    def __init__(self):
        self.dataset_service = DatasetService()
        self.chunked_upload_service = ChunkedUploadService()
        self.db = get_firestore_client()
        self.bucket = get_storage_bucket()
        self.settings = get_settings()
        
        # Initialize MongoDB service if enabled
        self.use_mongodb = self.settings.use_mongodb
        self.mongodb_service = MongoDBService() if self.use_mongodb else None
        self.batch_size = self.settings.batch_size
        self.max_workers = self.settings.max_workers
        
        # Firestore collections
        self.DATASET_COLLECTION = "datasets"
        self.CLASS_COLLECTION = "class_definitions"
    
    async def import_yolo_dataset(
        self, 
        dataset_name: str, 
        description: str,
        zip_file: UploadFile,
        class_names: List[str] = None,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> Dataset:
        """
        Import a YOLO format dataset from a ZIP file.
        
        The ZIP file should contain:
        - images/ directory with image files
        - labels/ directory with YOLO format label files
        - (optional) classes.txt with class names
        """
        try:
            # Print debug info
            print(f"Starting import of YOLO dataset: {dataset_name}")
            print(f"Class names provided: {class_names}")
            
            # Check if this is a small dataset (less than 100MB) or a large one
            content_length = zip_file.size if hasattr(zip_file, "size") else None
            print(f"Content length: {content_length}")
            
            # Create the dataset first
            dataset_data = DatasetCreate(name=dataset_name, description=description)
            dataset = await self.dataset_service.create_dataset(dataset_data)
            print(f"Created dataset with ID: {dataset.id}")
            
            # Store class names if provided
            if class_names:
                await self._store_class_definitions(dataset.id, class_names)
            
            if content_length is None or content_length < 100 * 1024 * 1024:  # Less than 100MB
                # Small dataset, process synchronously
                print(f"Processing small dataset synchronously")
                await self._process_small_dataset(dataset.id, zip_file, class_names)
            else:
                # Large dataset, use chunked upload and process in background
                if background_tasks:
                    print(f"Processing large dataset asynchronously with background tasks")
                    # Start processing in background
                    upload_meta = await self.chunked_upload_service.initiate_chunked_upload(
                        filename=f"{dataset.id}_dataset.zip",
                        total_size=content_length or 0  # If unknown, start with 0
                    )
                    
                    # First chunk is the current file content
                    first_chunk = await zip_file.read()
                    await self.chunked_upload_service.upload_chunk(
                        upload_id=upload_meta["upload_id"],
                        chunk_number=0,
                        total_chunks=1,  # Initially assume 1 chunk, will be updated if more come
                        chunk_data=UploadFile(filename="chunk0", file=io.BytesIO(first_chunk))
                    )
                    
                    # Update dataset status
                    dataset_ref = self.db.collection(self.DATASET_COLLECTION).document(dataset.id)
                    dataset_ref.update({
                        "status": "importing",
                        "upload_id": upload_meta["upload_id"]
                    })
                    
                    # Add background task to process when upload is complete
                    background_tasks.add_task(
                        self._finalize_large_dataset_import,
                        dataset_id=dataset.id,
                        upload_id=upload_meta["upload_id"],
                        class_names=class_names
                    )
                else:
                    # If no background_tasks provided, treat as small dataset
                    print(f"No background tasks available, processing large dataset synchronously")
                    await self._process_small_dataset(dataset.id, zip_file, class_names)
            
            print(f"Dataset import initiated successfully: {dataset.id}")
            return dataset
            
        except Exception as e:
            print(f"Error during dataset import: {str(e)}")
            # Try to update dataset status if it was created
            try:
                if 'dataset' in locals():
                    dataset_ref = self.db.collection(self.DATASET_COLLECTION).document(dataset.id)
                    dataset_ref.update({
                        "status": "error", 
                        "error_message": str(e)
                    })
            except Exception as update_error:
                print(f"Failed to update dataset error status: {update_error}")
                
            # Re-raise with more context
            raise HTTPException(
                status_code=500,
                detail=f"Failed to import dataset: {str(e)}"
            ) from e
        
    async def _process_small_dataset(self, dataset_id: str, zip_file: UploadFile, class_names: List[str] = None) -> None:
        """Process a small YOLO dataset synchronously."""
        # Create temporary directory for extraction
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp()
            print(f"Created temp directory at {temp_dir}")
            
            # Seek to beginning of file in case it was read before
            await zip_file.seek(0)
            
            # Save and extract ZIP file
            zip_path = os.path.join(temp_dir, "dataset.zip")
            print(f"Saving ZIP file to {zip_path}")
            
            # Read content from upload file
            content = await zip_file.read()
            print(f"Read {len(content)} bytes from uploaded file")
            
            # Write content to disk
            with open(zip_path, "wb") as f:
                f.write(content)
                
            print(f"ZIP file saved, checking if valid ZIP archive...")
            if not zipfile.is_zipfile(zip_path):
                raise HTTPException(
                    status_code=400,
                    detail="Uploaded file is not a valid ZIP archive"
                )
            
            # Extract ZIP file
            print(f"Extracting ZIP file...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                print(f"ZIP extracted. Contents: {os.listdir(temp_dir)}")
            
            # Check directory structure
            print(f"Validating YOLO format directory structure...")
            images_dir = os.path.join(temp_dir, "images")
            labels_dir = os.path.join(temp_dir, "labels")
            
            # Try to find the directories if they're in a subdirectory
            if not os.path.exists(images_dir) or not os.path.exists(labels_dir):
                print(f"Standard directory structure not found, searching for images and labels folders...")
                # Try to find images and labels directories
                for root, dirs, _ in os.walk(temp_dir):
                    if "images" in dirs and "labels" in dirs:
                        images_dir = os.path.join(root, "images")
                        labels_dir = os.path.join(root, "labels")
                        print(f"Found images and labels in: {root}")
                        break
            
            # Final check if directories exist
            if not os.path.exists(images_dir) or not os.path.exists(labels_dir):
                # Update dataset status to error
                dataset_ref = self.db.collection(self.DATASET_COLLECTION).document(dataset_id)
                dataset_ref.update({"status": "error", "error_message": "Invalid YOLO format"})
                
                raise HTTPException(
                    status_code=400,
                    detail="Invalid YOLO dataset format. Must contain 'images' and 'labels' directories."
                )
            
            # Read class names if available
            local_class_names = []
            print(f"Looking for classes.txt...")
            
            # Try to find classes.txt anywhere in the extracted directory
            classes_path = None
            for root, _, files in os.walk(temp_dir):
                if "classes.txt" in files:
                    classes_path = os.path.join(root, "classes.txt")
                    break
            
            if classes_path and os.path.exists(classes_path):
                print(f"Found classes.txt at: {classes_path}")
                with open(classes_path, "r") as f:
                    local_class_names = [line.strip() for line in f.readlines()]
                
                print(f"Class names from file: {local_class_names}")
                # Store class definitions
                await self._store_class_definitions(dataset_id, local_class_names)
            elif class_names:
                local_class_names = class_names
                print(f"Using provided class names: {local_class_names}")
            
            # Process images and labels
            print(f"Processing images and labels...")
            await self._process_yolo_files(dataset_id, images_dir, labels_dir)
            
            # Update dataset status
            print(f"Updating dataset status to ready...")
            dataset_ref = self.db.collection(self.DATASET_COLLECTION).document(dataset_id)
            dataset_ref.update({"status": "ready"})
            print(f"Dataset {dataset_id} import completed successfully")
            
        except Exception as e:
            print(f"Error processing small dataset: {str(e)}")
            # Update dataset status to error
            try:
                dataset_ref = self.db.collection(self.DATASET_COLLECTION).document(dataset_id)
                dataset_ref.update({"status": "error", "error_message": str(e)})
            except Exception as update_error:
                print(f"Failed to update dataset error status: {update_error}")
            raise
        finally:
            # Clean up temporary directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    print(f"Cleaned up temp directory: {temp_dir}")
                except Exception as e:
                    print(f"Error cleaning up temp directory: {e}")

        
    async def _finalize_large_dataset_import(self, dataset_id: str, upload_id: str, class_names: List[str] = None) -> None:
        """Finalize a large dataset import after chunked upload is complete."""
        try:
            # First finalize the chunked upload
            upload_meta = await self.chunked_upload_service.finalize_chunked_upload(upload_id)
            
            # Get the final zip file path
            zip_path = upload_meta.get("final_path")
            if not zip_path:
                raise Exception("Failed to finalize upload: missing final path")
            
            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download the zip file
                local_zip_path = os.path.join(temp_dir, "dataset.zip")
                blob = self.bucket.blob(zip_path)
                blob.download_to_filename(local_zip_path)
                
                # Extract ZIP file
                with zipfile.ZipFile(local_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Validate YOLO format structure
                images_dir = os.path.join(temp_dir, "images")
                labels_dir = os.path.join(temp_dir, "labels")
                
                if not os.path.exists(images_dir) or not os.path.exists(labels_dir):
                    # Update dataset status to error
                    dataset_ref = self.db.collection(self.DATASET_COLLECTION).document(dataset_id)
                    dataset_ref.update({"status": "error", "error_message": "Invalid YOLO format"})
                    return
                
                # Read class names if available
                local_class_names = []
                classes_path = os.path.join(temp_dir, "classes.txt")
                if os.path.exists(classes_path):
                    with open(classes_path, "r") as f:
                        local_class_names = [line.strip() for line in f.readlines()]
                    
                    # Store class definitions
                    await self._store_class_definitions(dataset_id, local_class_names)
                elif class_names:
                    local_class_names = class_names
                
                # Process images and labels in batches to handle large datasets
                await self._process_yolo_files_in_batches(dataset_id, images_dir, labels_dir)
                
                # Update dataset status
                dataset_ref = self.db.collection(self.DATASET_COLLECTION).document(dataset_id)
                dataset_ref.update({"status": "ready"})
                
        except Exception as e:
            # Update dataset status to error
            dataset_ref = self.db.collection(self.DATASET_COLLECTION).document(dataset_id)
            dataset_ref.update({"status": "error", "error_message": str(e)})
            raise
    
    async def _process_yolo_files(self, dataset_id: str, images_dir: str, labels_dir: str) -> None:
        """Process YOLO format image and label files."""
        logger.info(f"Processing YOLO files from images_dir: {images_dir}, labels_dir: {labels_dir}")
        
        # Find all image files recursively (handles train/val subdirectories)
        image_files = []
        for root, dirs, files in os.walk(images_dir):
            for file in files:
                if file.lower().endswith(tuple(self.settings.SUPPORTED_IMAGE_FORMATS)):
                    full_path = os.path.join(root, file)
                    # Calculate relative path from images_dir to maintain structure
                    rel_path = os.path.relpath(full_path, images_dir)
                    image_files.append((full_path, rel_path))
        
        logger.info(f"Found {len(image_files)} image files in {images_dir}")
        if image_files:
            logger.info(f"Sample image files: {[rel for _, rel in image_files[:5]]}")  # First 5 files
        
        # Check if we should use batch processing
        if len(image_files) > self.batch_size:
            logger.info(f"Using batch processing for {len(image_files)} images")
            await self._process_yolo_files_in_batches(dataset_id, images_dir, labels_dir)
            return
        
        # MongoDB batch storage lists
        mongo_images = []
        mongo_labels = []
        
        # Process all images, with or without labels
        processed_count = 0
        for img_path, img_rel_path in image_files:
            try:
                # Get corresponding label file using the same relative structure
                base_name = os.path.splitext(os.path.basename(img_path))[0]
                label_file = f"{base_name}.txt"
                
                # Construct label path using the same relative directory structure
                img_dir_rel = os.path.dirname(img_rel_path)  # e.g., "train" or "val"
                if img_dir_rel:
                    label_path = os.path.join(labels_dir, img_dir_rel, label_file)
                else:
                    label_path = os.path.join(labels_dir, label_file)
                
                # Check if label file exists
                label_exists = os.path.exists(label_path)
                if not label_exists:
                    # Try alternative locations if the label doesn't exist in the expected path
                    alt_label_paths = [
                        os.path.join(labels_dir, label_file),  # Try root labels directory
                        os.path.join(labels_dir, "train", label_file),  # Try train subdirectory
                        os.path.join(labels_dir, "val", label_file)  # Try val subdirectory
                    ]
                    
                    for alt_path in alt_label_paths:
                        if os.path.exists(alt_path):
                            label_path = alt_path
                            label_exists = True
                            logger.info(f"Found label in alternative location: {label_path}")
                            break
                
                if not label_exists:
                    logger.info(f"Processing image {img_path} without labels (for annotation)")
                else:
                    logger.info(f"Processing image {img_path} with labels {label_path}")
                
                # Process image
                with open(img_path, "rb") as f:
                    img_bytes = f.read()
                    
                # Get image dimensions
                with PILImage.open(io.BytesIO(img_bytes)) as img:
                    width, height = img.size
                    
                # Create an UploadFile object
                upload_file = UploadFile(
                    filename=os.path.basename(img_path),
                    file=io.BytesIO(img_bytes)
                )
                
                # Upload image to dataset
                logger.info(f"Uploading image {os.path.basename(img_path)} to dataset {dataset_id}")
                image = await self.dataset_service.upload_image_to_dataset(
                    dataset_id=dataset_id,
                    file=upload_file,
                    width=width,
                    height=height
                )
                logger.info(f"Image uploaded successfully with ID: {image.id}")
                
                # Store in MongoDB if enabled
                if self.use_mongodb and self.mongodb_service and self.mongodb_service.is_connected():
                    # Prepare image data for MongoDB
                    mongo_image = image.to_dict()
                    mongo_images.append(mongo_image)
                
                # Process labels only if they exist
                if label_exists:
                    labels = await self._process_yolo_labels(image.id, label_path)
                    
                    # Store labels in MongoDB if enabled
                    if self.use_mongodb and self.mongodb_service and self.mongodb_service.is_connected() and labels:
                        mongo_labels.extend([label.to_dict() for label in labels])
                
                processed_count += 1
                if processed_count % 10 == 0 or processed_count == len(image_files):
                    logger.info(f"Processed {processed_count}/{len(image_files)} images")
                
                # Store batch in MongoDB if enough items accumulated
                if self.use_mongodb and self.mongodb_service and self.mongodb_service.is_connected():
                    if len(mongo_images) >= self.batch_size:
                        self.mongodb_service.store_images_batch(mongo_images)
                        mongo_images = []
                    
                    if len(mongo_labels) >= self.batch_size:
                        self.mongodb_service.store_labels_batch(mongo_labels)
                        mongo_labels = []
                
            except Exception as e:
                logger.error(f"Error processing image {img_path}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        # Store any remaining items in MongoDB
        if self.use_mongodb and self.mongodb_service and self.mongodb_service.is_connected():
            if mongo_images:
                self.mongodb_service.store_images_batch(mongo_images)
            
            if mongo_labels:
                self.mongodb_service.store_labels_batch(mongo_labels)
        
        logger.info(f"Completed processing {processed_count} images out of {len(image_files)} total")
    
    async def _process_yolo_files_in_batches(self, dataset_id: str, images_dir: str, labels_dir: str) -> None:
        """Process YOLO format image and label files in batches to handle large datasets."""
        # Get image files recursively (handles train/val subdirectories)
        image_files = []
        for root, dirs, files in os.walk(images_dir):
            for file in files:
                if file.lower().endswith(tuple(self.settings.SUPPORTED_IMAGE_FORMATS)):
                    full_path = os.path.join(root, file)
                    # Calculate relative path from images_dir to maintain structure
                    rel_path = os.path.relpath(full_path, images_dir)
                    image_files.append((full_path, rel_path))
        
        logger.info(f"Found {len(image_files)} image files for batch processing")
        
        # Update import status in MongoDB if enabled
        if self.use_mongodb and self.mongodb_service and self.mongodb_service.is_connected():
            self.mongodb_service.update_import_status(
                dataset_id=dataset_id,
                status="importing",
                progress=0.0,
                message=f"Starting import of {len(image_files)} images"
            )
        
        # Process in batches
        total_images = len(image_files)
        total_batches = (total_images + self.batch_size - 1) // self.batch_size
        total_processed = 0
        start_time = time.time()
        
        for i in range(0, total_images, self.batch_size):
            batch = image_files[i:i+self.batch_size]
            batch_processed = 0
            
            # MongoDB batch storage lists
            mongo_images = []
            mongo_labels = []
            
            # Process batch of images
            for img_path, img_rel_path in batch:
                try:
                    # Get corresponding label file using the same relative structure
                    base_name = os.path.splitext(os.path.basename(img_path))[0]
                    label_file = f"{base_name}.txt"
                    
                    # Construct label path using the same relative directory structure
                    img_dir_rel = os.path.dirname(img_rel_path)  # e.g., "train" or "val"
                    if img_dir_rel:
                        label_path = os.path.join(labels_dir, img_dir_rel, label_file)
                    else:
                        label_path = os.path.join(labels_dir, label_file)
                    
                    # Check if label file exists
                    label_exists = os.path.exists(label_path)
                    if not label_exists:
                        # Try alternative locations if the label doesn't exist in the expected path
                        alt_label_paths = [
                            os.path.join(labels_dir, label_file),  # Try root labels directory
                            os.path.join(labels_dir, "train", label_file),  # Try train subdirectory
                            os.path.join(labels_dir, "val", label_file)  # Try val subdirectory
                        ]
                        
                        for alt_path in alt_label_paths:
                            if os.path.exists(alt_path):
                                label_path = alt_path
                                label_exists = True
                                logger.info(f"Found label in alternative location: {label_path}")
                                break
                    
                    if not label_exists:
                        logger.info(f"Processing image {img_path} without labels (for annotation)")
                    else:
                        logger.info(f"Processing image {img_path} with labels {label_path}")
                    
                    # Process image
                    with open(img_path, "rb") as f:
                        img_bytes = f.read()
                        
                    # Get image dimensions
                    with PILImage.open(io.BytesIO(img_bytes)) as img:
                        width, height = img.size
                        
                    # Create an UploadFile object
                    upload_file = UploadFile(
                        filename=os.path.basename(img_path),
                        file=io.BytesIO(img_bytes)
                    )
                    
                    # Upload image to dataset
                    image = await self.dataset_service.upload_image_to_dataset(
                        dataset_id=dataset_id,
                        file=upload_file,
                        width=width,
                        height=height
                    )
                    
                    # Store in MongoDB if enabled
                    if self.use_mongodb and self.mongodb_service and self.mongodb_service.is_connected():
                        # Prepare image data for MongoDB
                        mongo_image = image.to_dict()
                        mongo_images.append(mongo_image)
                    
                    # Process labels only if they exist
                    if label_exists:
                        labels = await self._process_yolo_labels(image.id, label_path)
                        
                        # Store labels in MongoDB if enabled
                        if self.use_mongodb and self.mongodb_service and self.mongodb_service.is_connected() and labels:
                            mongo_labels.extend([label.to_dict() for label in labels])
                    
                    batch_processed += 1
                    
                except Exception as e:
                    logger.error(f"Error processing image {img_path} in batch: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # Store batch in MongoDB
            if self.use_mongodb and self.mongodb_service and self.mongodb_service.is_connected():
                if mongo_images:
                    self.mongodb_service.store_images_batch(mongo_images)
                
                if mongo_labels:
                    self.mongodb_service.store_labels_batch(mongo_labels)
            
            # Update progress
            total_processed += batch_processed
            progress = total_processed / total_images
            elapsed_time = time.time() - start_time
            images_per_second = total_processed / elapsed_time if elapsed_time > 0 else 0
            estimated_remaining = (total_images - total_processed) / images_per_second if images_per_second > 0 else 0
            
            # Update dataset with progress and image count
            dataset_ref = self.db.collection(self.DATASET_COLLECTION).document(dataset_id)
            dataset_ref.update({
                "import_progress": min(100, int(progress * 100)),
                "image_count": total_processed
            })
            
            logger.info(f"Processed batch {i//self.batch_size + 1}/{total_batches}: "
                      f"{batch_processed}/{len(batch)} images. "
                      f"Total: {total_processed}/{total_images} ({progress:.1%}). "
                      f"Speed: {images_per_second:.1f} img/s. "
                      f"ETA: {estimated_remaining:.1f}s")
            
            # Update import status in MongoDB
            if self.use_mongodb and self.mongodb_service and self.mongodb_service.is_connected():
                self.mongodb_service.update_import_status(
                    dataset_id=dataset_id,
                    status="importing",
                    progress=progress,
                    message=f"Processed {total_processed}/{total_images} images ({progress:.1%})"
                )
        
        # Final update
        if self.use_mongodb and self.mongodb_service and self.mongodb_service.is_connected():
            self.mongodb_service.update_import_status(
                dataset_id=dataset_id,
                status="completed",
                progress=1.0,
                message=f"Completed import of {total_processed}/{total_images} images"
            )
        
        logger.info(f"Completed batch processing: {total_processed}/{total_images} images in {time.time() - start_time:.1f}s")

    async def _process_single_image(self, dataset_id: str, images_dir: str, img_file: str, label_path: str) -> None:
        """Process a single image and its labels."""
        # Process image
        img_path = os.path.join(images_dir, img_file)
        with open(img_path, "rb") as f:
            img_bytes = f.read()
            
        # Get image dimensions
        with PILImage.open(io.BytesIO(img_bytes)) as img:
            width, height = img.size
            
        # Create an UploadFile object
        upload_file = UploadFile(
            filename=os.path.basename(img_path),
            file=io.BytesIO(img_bytes)
        )
        
        # Upload image to dataset
        image = await self.dataset_service.upload_image_to_dataset(
            dataset_id=dataset_id,
            file=upload_file,
            width=width,
            height=height
        )
        
        # Process labels
        if os.path.exists(label_path):
            labels = await self._process_yolo_labels(image.id, label_path)
    
    async def _process_yolo_labels(self, image_id: str, label_path: str) -> List[Label]:
        """Process YOLO format label file for an image.
        
        Args:
            image_id: The ID of the image to associate labels with
            label_path: Path to the YOLO format label file
            
        Returns:
            List of Label objects created
        """
        labels = []
        try:
            with open(label_path, "r") as f:
                label_lines = f.readlines()
            
            logger.info(f"Processing {len(label_lines)} labels for image {image_id}")
            
            for line in label_lines:
                # YOLO format: class_id x_center y_center width height
                parts = line.strip().split()
                if len(parts) != 5:
                    logger.warning(f"Invalid label format in {label_path}: {line}")
                    continue
                    
                try:
                    class_id = int(parts[0])
                    x_center = float(parts[1])
                    y_center = float(parts[2])
                    width = float(parts[3])
                    height = float(parts[4])
                    
                    # Validate coordinates (YOLO uses normalized coordinates 0-1)
                    if not (0 <= x_center <= 1 and 0 <= y_center <= 1 and 
                            0 < width <= 1 and 0 < height <= 1):
                        logger.warning(f"Invalid coordinates in {label_path}: {line}")
                        continue
                    
                    # Create label
                    label_data = LabelCreate(
                        class_id=class_id,
                        x_center=x_center,
                        y_center=y_center,
                        width=width,
                        height=height
                    )
                    
                    # Store label in Firestore
                    label = await self.dataset_service.create_label(image_id, label_data)
                    labels.append(label)
                    
                except Exception as e:
                    logger.error(f"Error processing label: {str(e)}")
                    continue
        except Exception as e:
            logger.error(f"Error opening label file {label_path}: {str(e)}")
        
        return labels
    
    async def _store_class_definitions(self, dataset_id: str, class_names: List[str]) -> None:
        """Store class definitions for a dataset."""
        if not class_names:
            logger.info("No class names provided, skipping class definition storage")
            return
            
        try:
            logger.info(f"Storing {len(class_names)} class definitions for dataset {dataset_id}")
            
            # Prepare batch storage for MongoDB
            mongo_class_defs = []
            batch = self.db.batch()
            
            for idx, name in enumerate(class_names):
                if not name:  # Skip empty class names
                    continue
                    
                class_def = ClassDefinition(
                    id=f"{dataset_id}_{idx}",
                    dataset_id=dataset_id,
                    class_id=idx,
                    name=name,
                    description=f"Class {idx}: {name}"
                )
                
                # Add to Firestore batch
                class_ref = self.db.collection(self.CLASS_COLLECTION).document(class_def.id)
                batch.set(class_ref, class_def.to_dict())
                
                # Add to MongoDB batch
                if self.use_mongodb and self.mongodb_service and self.mongodb_service.is_connected():
                    mongo_class_defs.append(class_def.to_dict())
            
            # Commit Firestore batch
            batch.commit()
            
            # Store class definitions in MongoDB
            if self.use_mongodb and self.mongodb_service and self.mongodb_service.is_connected() and mongo_class_defs:
                logger.info(f"Storing {len(mongo_class_defs)} class definitions in MongoDB for dataset {dataset_id}")
                self.mongodb_service.store_class_definitions_batch(mongo_class_defs)
                
            logger.info(f"Stored {len(class_names)} class definitions for dataset {dataset_id}")
        except Exception as e:
            logger.error(f"Error storing class definitions: {e}")
            # Don't fail the entire import if class definitions can't be stored
            # Just log the error and continue
        
    async def add_chunk_to_dataset(self, dataset_id: str, upload_id: str, 
                                   chunk_number: int, total_chunks: int, 
                                   chunk_file: UploadFile) -> Dict[str, Any]:
        """Add a chunk to an ongoing dataset upload."""
        # Verify dataset exists
        dataset_ref = self.db.collection(self.DATASET_COLLECTION).document(dataset_id)
        dataset_doc = dataset_ref.get()
        
        if not dataset_doc.exists:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Upload chunk
        result = await self.chunked_upload_service.upload_chunk(
            upload_id=upload_id,
            chunk_number=chunk_number,
            total_chunks=total_chunks,
            chunk_data=chunk_file
        )
        
        # If this is the last chunk, trigger background processing
        if result["status"] == "ready_for_finalization":
            # This would normally be done with a Cloud Function or Cloud Run job
            # For now, we'll just note that it should be finalized
            dataset_ref.update({
                "status": "finalizing",
                "last_updated": self.dataset_service.timestamp_now()
            })
        
        return result
        
    async def get_import_status(self, dataset_id: str) -> Dict[str, Any]:
        """
        Get the status of a dataset import.
        
        If MongoDB is enabled, it will check MongoDB first for more detailed status information.
        Otherwise, it will fall back to Firestore.
        
        Args:
            dataset_id: The ID of the dataset to check status for
            
        Returns:
            Dictionary with import status information
        """
        try:
            # Check MongoDB first if enabled
            if self.use_mongodb and self.mongodb_service and self.mongodb_service.is_connected():
                try:
                    mongo_status = self.mongodb_service.get_import_status(dataset_id)
                    if mongo_status:
                        logger.info(f"Found import status in MongoDB for dataset {dataset_id}")
                        return mongo_status
                except Exception as e:
                    logger.error(f"Error retrieving status from MongoDB: {str(e)}")
                    # Continue to Firestore as fallback
            
            # Fall back to Firestore
            logger.info(f"Checking Firestore for import status of dataset {dataset_id}")
            dataset_ref = self.db.collection(self.DATASET_COLLECTION).document(dataset_id)
            dataset_doc = dataset_ref.get()
            
            if not dataset_doc.exists:
                logger.warning(f"Dataset {dataset_id} not found in Firestore")
                return {
                    "dataset_id": dataset_id,
                    "status": "not_found",
                    "message": "Dataset not found or import not started",
                    "timestamp": self.dataset_service.timestamp_now()
                }
                
            dataset = Dataset.from_dict(dataset_doc.to_dict())
            
            # If there's an upload_id, get upload status
            status_data = {
                "dataset_id": dataset_id,
                "status": dataset.status or "unknown",
                "image_count": dataset.image_count or 0,
                "import_progress": dataset.import_progress or 0,
                "last_updated": dataset.last_updated,
                "timestamp": self.dataset_service.timestamp_now()
            }
            
            if dataset.upload_id:
                try:
                    upload_status = await self.chunked_upload_service.get_upload_status(dataset.upload_id)
                    status_data["upload_status"] = upload_status
                except Exception as e:
                    logger.error(f"Error getting upload status: {str(e)}")
                    status_data["upload_status"] = {"status": "unknown", "error": str(e)}
            
            # Store status in MongoDB for future reference
            if self.use_mongodb and self.mongodb_service and self.mongodb_service.is_connected():
                try:
                    self.mongodb_service.update_import_status(
                        dataset_id=dataset_id,
                        status=dataset.status or "unknown",
                        progress=dataset.import_progress / 100 if dataset.import_progress else 0,
                        message=f"Dataset has {dataset.image_count or 0} images",
                        additional_data=status_data
                    )
                except Exception as e:
                    logger.error(f"Error updating MongoDB status: {str(e)}")
            
            return status_data
            
        except Exception as e:
            logger.error(f"Unexpected error in get_import_status: {str(e)}")
            # Return a minimal status rather than raising an exception
            return {
                "dataset_id": dataset_id,
                "status": "error",
                "message": f"Error retrieving import status: {str(e)}",
                "timestamp": self.dataset_service.timestamp_now()
            }
