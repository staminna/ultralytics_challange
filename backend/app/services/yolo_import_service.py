import os
import io
import zipfile
import tempfile
import shutil
import asyncio
from typing import Dict, List, Tuple, Set, Optional, Any, BinaryIO
from fastapi import UploadFile, HTTPException, BackgroundTasks
from PIL import Image as PILImage

from .dataset_service import DatasetService
from .chunked_upload_service import ChunkedUploadService
from ..models.firestore_models import Dataset, Image, Label, ClassDefinition
from ..schemas.dataset import DatasetCreate, LabelCreate
from ..core.config import get_settings
from ..core.gcp import get_firestore_client, get_storage_bucket


class YoloImportService:
    """Service for importing YOLO format datasets."""
    
    def __init__(self):
        self.dataset_service = DatasetService()
        self.chunked_upload_service = ChunkedUploadService()
        self.db = get_firestore_client()
        self.bucket = get_storage_bucket()
        self.settings = get_settings()
        
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
        print(f"Processing YOLO files from images_dir: {images_dir}, labels_dir: {labels_dir}")
        
        # Find all image files recursively (handles train/val subdirectories)
        image_files = []
        for root, dirs, files in os.walk(images_dir):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    full_path = os.path.join(root, file)
                    # Calculate relative path from images_dir to maintain structure
                    rel_path = os.path.relpath(full_path, images_dir)
                    image_files.append((full_path, rel_path))
        
        print(f"Found {len(image_files)} image files in {images_dir}")
        if image_files:
            print(f"Sample image files: {[rel for _, rel in image_files[:5]]}")  # First 5 files
        
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
                    print(f"Processing image {img_path} without labels (for annotation)")
                else:
                    print(f"Processing image {img_path} with labels {label_path}")
                
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
                print(f"Uploading image {os.path.basename(img_path)} to dataset {dataset_id}")
                image = await self.dataset_service.upload_image_to_dataset(
                    dataset_id=dataset_id,
                    file=upload_file,
                    width=width,
                    height=height
                )
                print(f"Image uploaded successfully with ID: {image.id}")
                
                # Process labels
                if label_exists:
                    await self._process_yolo_labels(image.id, label_path)
                processed_count += 1
                print(f"Processed {processed_count}/{len(image_files)} images")
                
            except Exception as e:
                print(f"Error processing image {img_path}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"Completed processing {processed_count} images out of {len(image_files)} total")
    
    async def _process_yolo_files_in_batches(self, dataset_id: str, images_dir: str, labels_dir: str, batch_size: int = 50) -> None:
        """Process YOLO format image and label files in batches to handle large datasets."""
        # Get image files
        image_files = []
        for root, dirs, files in os.walk(images_dir):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    full_path = os.path.join(root, file)
                    # Calculate relative path from images_dir to maintain structure
                    rel_path = os.path.relpath(full_path, images_dir)
                    image_files.append((full_path, rel_path))
        
        # Process in batches
        total_images = len(image_files)
        for i in range(0, total_images, batch_size):
            batch = image_files[i:i+batch_size]
            tasks = []
            
            for img_path, img_rel_path in batch:
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
                    print(f"Processing image {img_path} without labels (for annotation)")
                else:
                    print(f"Processing image {img_path} with labels {label_path}")
                
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
                print(f"Uploading image {os.path.basename(img_path)} to dataset {dataset_id}")
                image = await self.dataset_service.upload_image_to_dataset(
                    dataset_id=dataset_id,
                    file=upload_file,
                    width=width,
                    height=height
                )
                print(f"Image uploaded successfully with ID: {image.id}")
                
                # Process labels
                if label_exists:
                    await self._process_yolo_labels(image.id, label_path)
                
                # Update dataset with progress
                progress = min(100, int((i + len(batch)) / total_images * 100))
                dataset_ref = self.db.collection(self.DATASET_COLLECTION).document(dataset_id)
                dataset_ref.update({"import_progress": progress})
    
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
            await self._process_yolo_labels(image.id, label_path)
    
    async def _process_yolo_labels(self, image_id: str, label_path: str) -> None:
        """Process YOLO format label file for an image."""
        with open(label_path, "r") as f:
            label_lines = f.readlines()
        
        for line in label_lines:
            # YOLO format: class_id x_center y_center width height
            parts = line.strip().split()
            if len(parts) != 5:
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
                    continue
                
                # Create label
                label_data = LabelCreate(
                    class_id=class_id,
                    x_center=x_center,
                    y_center=y_center,
                    width=width,
                    height=height
                )
                
                await self.dataset_service.create_label(image_id, label_data)
                
            except (ValueError, IndexError):
                # Skip invalid label entries
                continue
                
    async def _store_class_definitions(self, dataset_id: str, class_names: List[str]) -> None:
        """Store class definitions for a dataset."""
        if not class_names:
            print("No class names provided, skipping class definition storage")
            return
            
        try:
            batch = self.db.batch()
            
            for idx, name in enumerate(class_names):
                if not name:  # Skip empty class names
                    continue
                    
                class_def = ClassDefinition(
                    class_id=idx,
                    name=name,
                    description=f"Class {idx}: {name}"
                )
                
                # Add to batch
                class_ref = self.db.collection(self.CLASS_COLLECTION).document()
                batch.set(class_ref, class_def.to_dict())
                
            # Commit batch
            batch.commit()
            print(f"Stored {len(class_names)} class definitions for dataset {dataset_id}")
        except Exception as e:
            print(f"Error storing class definitions: {e}")
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
        """Get the status of a dataset import."""
        # Verify dataset exists
        dataset_ref = self.db.collection(self.DATASET_COLLECTION).document(dataset_id)
        dataset_doc = dataset_ref.get()
        
        if not dataset_doc.exists:
            raise HTTPException(status_code=404, detail="Dataset not found")
            
        dataset = Dataset.from_dict(dataset_doc.to_dict())
        
        # If there's an upload_id, get upload status
        upload_status = None
        if hasattr(dataset, "upload_id") and dataset.upload_id:
            upload_meta = await self.chunked_upload_service._get_upload_metadata(dataset.upload_id)
            if upload_meta:
                upload_status = upload_meta
        
        return {
            "dataset_id": dataset_id,
            "status": getattr(dataset, "status", "unknown"),
            "progress": getattr(dataset, "import_progress", 0),
            "upload_status": upload_status
        }
