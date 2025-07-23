import os
import zipfile
import tempfile
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from beanie import PydanticObjectId
import logging

import yaml
from fastapi import UploadFile, HTTPException, status

from ..core.storage import get_storage_backend, StorageBackend
from ..core.storage_paths import StoragePaths
from ..models.mongo_models import Dataset, Image, Label, ClassDefinition

logger = logging.getLogger(__name__)

class YoloImportService:
    def __init__(self):
        self.storage = get_storage_backend()

    async def import_yolo_dataset(self, file: UploadFile, dataset_name: Optional[str] = None) -> Dataset:
        """Import a YOLO dataset with chunked processing for large datasets up to 100GB."""
        
        # Use provided name or derive from filename
        if not dataset_name:
            dataset_name = Path(file.filename).stem
        
        # Enhanced duplicate checking
        duplicate_info = await self._check_for_duplicates(file, dataset_name)
        if duplicate_info:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Dataset already exists: {duplicate_info}"
            )
        
        logger.info(f"Starting import of dataset: {dataset_name}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            zip_path = temp_path / file.filename
            
            # Save uploaded file in chunks to handle large files
            logger.info("Saving uploaded file...")
            with open(zip_path, "wb") as buffer:
                chunk_size = 8192  # 8KB chunks
                while chunk := await file.read(chunk_size):
                    buffer.write(chunk)
            
            # Calculate file hash for integrity (for smaller files only)
            file_size = zip_path.stat().st_size
            file_hash = "large_file" if file_size > 1024*1024*100 else hashlib.md5(zip_path.read_bytes()).hexdigest()
            logger.info(f"File size: {file_size / (1024*1024):.1f} MB, Hash: {file_hash}")
            
            # Extract ZIP file
            try:
                logger.info("Extracting ZIP file...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)
                logger.info(f"Successfully extracted ZIP file")
            except zipfile.BadZipFile:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid ZIP file"
                )
            
            # Find the dataset directory (might be nested)
            dataset_path = self._find_dataset_root(temp_path)
            if not dataset_path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No valid YOLO dataset structure found"
                )
            
            # Validate YOLO structure
            validation_result = await self._validate_yolo_structure(dataset_path)
            if not validation_result["valid"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid YOLO dataset: {validation_result['error']}"
                )
            
            logger.info(f"Dataset validation passed: {validation_result['summary']}")
            
            # Create dataset record with processing status
            dataset = Dataset(
                name=dataset_name,
                description=f"YOLO dataset imported from {file.filename}",
                format="yolo",
                file_hash=file_hash,
                metadata={
                    "original_filename": file.filename,
                    "import_summary": validation_result["summary"],
                    "images_count": validation_result["images_count"],
                    "labels_count": validation_result["labels_count"],
                    "processing_status": "processing",
                    "processed_images": 0
                }
            )
            await dataset.insert()
            
            try:
                # Process files with chunked processing
                await self._process_yolo_files_chunked(dataset_path, dataset)
                
                # Update status to completed
                dataset.metadata["processing_status"] = "completed"
                await dataset.save()
                
                # Return summary response instead of full dataset
                return self._create_import_response(dataset)
                
            except Exception as e:
                # Update status to failed but keep dataset for debugging
                dataset.metadata["processing_status"] = "failed"
                dataset.metadata["error_message"] = str(e)
                await dataset.save()
                
                logger.error(f"Failed to process dataset: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to process dataset: {str(e)}"
                )

    async def _process_yolo_files_chunked(self, dataset_path: Path, dataset: Dataset):
        """Process YOLO dataset files with chunked processing for large datasets."""
        
        # Load class definitions
        class_names = await self._load_class_definitions(dataset_path, dataset)
        class_map = {name: class_def for name, class_def in class_names.items()}
        
        # Find images and labels directories (support nested structure)
        images_paths = self._find_images_directories(dataset_path)
        labels_paths = self._find_labels_directories(dataset_path)
        
        if not images_paths:
            raise ValueError("No images directory found in dataset")
        
        logger.info(f"Found {len(images_paths)} image directories")
        
        # Collect all image files first
        all_image_files = []
        for images_path in images_paths:
            for image_file in images_path.rglob('*.*'):
                if image_file.is_file() and self._is_image_file(image_file):
                    # Find corresponding labels directory
                    labels_path = self._find_corresponding_labels_path(images_path, labels_paths)
                    all_image_files.append((image_file, images_path, labels_path))
        
        total_images = len(all_image_files)
        logger.info(f"Found {total_images} total images to process")
        
        # Process in chunks to avoid memory issues and timeouts
        chunk_size = 50  # Process 50 images at a time
        processed_count = 0
        
        for i in range(0, total_images, chunk_size):
            chunk = all_image_files[i:i + chunk_size]
            logger.info(f"Processing chunk {i//chunk_size + 1}/{(total_images + chunk_size - 1)//chunk_size} ({len(chunk)} images)")
            
            # Process chunk
            for image_file, images_path, labels_path in chunk:
                try:
                    # Upload image to storage using consistent path structure
                    storage_path = StoragePaths.dataset_image_file_path(dataset.id, image_file.name)
                    storage_url = await self.storage.upload_file(image_file, storage_path)
                    
                    # Get image dimensions (placeholder for now)
                    width, height = await self._get_image_dimensions(image_file)
                    
                    # Create image record
                    new_image = Image(
                        dataset_id=dataset.id,
                        file_name=image_file.name,
                        gcs_path=storage_url,
                        width=width,
                        height=height
                    )
                    await new_image.insert()
                    dataset.images.append(new_image)
                    
                    # Process corresponding label file if it exists
                    if labels_path:
                        label_file = labels_path / (image_file.stem + '.txt')
                        if label_file.exists():
                            await self._process_label_file(label_file, new_image, class_map)
                    
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process image {image_file}: {str(e)}")
                    continue
            
            # Update progress in dataset metadata
            dataset.metadata["processed_images"] = processed_count
            await dataset.save()
            
            # Log progress
            progress_pct = (processed_count / total_images) * 100
            logger.info(f"Progress: {processed_count}/{total_images} ({progress_pct:.1f}%)")
            
            # Small delay to prevent overwhelming the system
            import asyncio
            await asyncio.sleep(0.1)
        
        logger.info(f"Successfully processed {processed_count} images")
    
    def _find_dataset_root(self, temp_path: Path) -> Optional[Path]:
        """Find the root directory of the YOLO dataset."""
        
        # Check if temp_path itself is the dataset root
        if self._is_yolo_dataset_root(temp_path):
            return temp_path
        
        # Look for dataset root in subdirectories
        for item in temp_path.iterdir():
            if item.is_dir():
                if self._is_yolo_dataset_root(item):
                    return item
                
                # Check one level deeper
                for subitem in item.iterdir():
                    if subitem.is_dir() and self._is_yolo_dataset_root(subitem):
                        return subitem
        
        return None
    
    def _is_yolo_dataset_root(self, path: Path) -> bool:
        """Check if a directory is a YOLO dataset root."""
        
        try:
            # Look for images directory or image files
            has_images = False
            
            # Check for images directory
            if (path / 'images').exists():
                has_images = True
            
            # Check for image files directly in the directory
            for item in path.iterdir():
                if item.is_file() and self._is_image_file(item):
                    has_images = True
                    break
            
            # Check for subdirectories with images
            for item in path.iterdir():
                if item.is_dir():
                    try:
                        for subitem in item.iterdir():
                            if subitem.is_file() and self._is_image_file(subitem):
                                has_images = True
                                break
                    except (OSError, PermissionError):
                        continue
                if has_images:
                    break
            
            return has_images
            
        except (OSError, PermissionError) as e:
            logger.warning(f"Error checking dataset root {path}: {e}")
            return False

    async def _process_yolo_files(self, dataset_path: Path, dataset: Dataset):
        """Process YOLO dataset files with enhanced structure support."""
        
        # Load class definitions
        class_names = await self._load_class_definitions(dataset_path, dataset)
        class_map = {name: class_def for name, class_def in class_names.items()}
        
        # Find images and labels directories (support nested structure)
        images_paths = self._find_images_directories(dataset_path)
        labels_paths = self._find_labels_directories(dataset_path)
        
        if not images_paths:
            raise ValueError("No images directory found in dataset")
        
        logger.info(f"Found {len(images_paths)} image directories")
        
        processed_count = 0
        
        # Process each images directory
        for images_path in images_paths:
            # Find corresponding labels directory
            labels_path = self._find_corresponding_labels_path(images_path, labels_paths)
            
            # Process all image files in this directory
            for image_file in images_path.rglob('*.*'):
                if not image_file.is_file() or not self._is_image_file(image_file):
                    continue
                
                try:
                    # Upload image to storage using consistent path structure
                    storage_path = StoragePaths.dataset_image_file_path(dataset.id, image_file.name)
                    storage_url = await self.storage.upload_file(image_file, storage_path)
                    
                    # Get image dimensions (placeholder for now)
                    width, height = await self._get_image_dimensions(image_file)
                    
                    # Create image record
                    new_image = Image(
                        dataset_id=dataset.id,
                        file_name=image_file.name,
                        gcs_path=storage_url,
                        width=width,
                        height=height
                    )
                    await new_image.insert()
                    dataset.images.append(new_image)
                    
                    # Process corresponding label file if it exists
                    if labels_path:
                        label_file = labels_path / (image_file.stem + '.txt')
                        if label_file.exists():
                            await self._process_label_file(label_file, new_image, class_map)
                    
                    processed_count += 1
                    if processed_count % 100 == 0:
                        logger.info(f"Processed {processed_count} images")
                        
                except Exception as e:
                    logger.error(f"Failed to process image {image_file}: {str(e)}")
                    continue
        
        await dataset.save()
        logger.info(f"Successfully processed {processed_count} images")
    
    async def _check_for_duplicates(self, file: UploadFile, dataset_name: str) -> Optional[str]:
        """Enhanced duplicate checking with multiple criteria."""
        
        try:
            # Check by exact name
            existing = await Dataset.find_one(Dataset.name == dataset_name)
            if existing:
                return f"Exact name match: {existing.name}"
            
            # Check by normalized name variations
            normalized_names = [
                dataset_name.lower(),
                dataset_name.replace('_', '-'),
                dataset_name.replace('-', '_'),
                dataset_name.replace(' ', '_'),
                dataset_name.replace(' ', '-')
            ]
            
            for norm_name in normalized_names:
                try:
                    existing = await Dataset.find_one(Dataset.name == norm_name)
                    if existing:
                        return f"Similar name match: {existing.name}"
                except Exception as e:
                    logger.warning(f"Error checking duplicate for {norm_name}: {e}")
                    continue
            
            # TODO: Add file hash checking for exact content duplicates
            return None
            
        except Exception as e:
            logger.warning(f"Error in duplicate checking, proceeding with import: {e}")
            # If duplicate checking fails, proceed with import
            return None
    
    async def _validate_yolo_structure(self, dataset_path: Path) -> Dict[str, any]:
        """Validate YOLO dataset structure and return summary."""
        
        images_dirs = self._find_images_directories(dataset_path)
        labels_dirs = self._find_labels_directories(dataset_path)
        
        if not images_dirs:
            return {
                "valid": False,
                "error": "No images directory found"
            }
        
        # Count files
        total_images = 0
        total_labels = 0
        
        for images_dir in images_dirs:
            image_files = [f for f in images_dir.rglob('*.*') if self._is_image_file(f)]
            total_images += len(image_files)
        
        for labels_dir in labels_dirs:
            label_files = [f for f in labels_dir.rglob('*.txt') if f.is_file()]
            total_labels += len(label_files)
        
        # Check for class definitions
        has_classes = (dataset_path / 'classes.txt').exists() or (dataset_path / 'data.yaml').exists()
        
        summary = f"{total_images} images, {total_labels} labels"
        if has_classes:
            summary += ", with class definitions"
        
        return {
            "valid": True,
            "summary": summary,
            "images_count": total_images,
            "labels_count": total_labels,
            "has_classes": has_classes
        }
    
    def _find_images_directories(self, dataset_path: Path) -> List[Path]:
        """Find all images directories in the dataset."""
        images_dirs = []
        
        # Look for standard 'images' directory
        if (dataset_path / 'images').exists():
            images_dirs.append(dataset_path / 'images')
        
        # Look for train/val/test subdirectories
        for subdir in ['train', 'val', 'test', 'valid']:
            images_subdir = dataset_path / 'images' / subdir
            if images_subdir.exists():
                images_dirs.append(images_subdir)
        
        # Look for direct train/val directories with images
        for subdir in ['train', 'val', 'test', 'valid']:
            direct_dir = dataset_path / subdir
            if direct_dir.exists() and any(self._is_image_file(f) for f in direct_dir.iterdir() if f.is_file()):
                images_dirs.append(direct_dir)
        
        return images_dirs
    
    def _find_labels_directories(self, dataset_path: Path) -> List[Path]:
        """Find all labels directories in the dataset."""
        labels_dirs = []
        
        # Look for standard 'labels' directory
        if (dataset_path / 'labels').exists():
            labels_dirs.append(dataset_path / 'labels')
        
        # Look for train/val/test subdirectories
        for subdir in ['train', 'val', 'test', 'valid']:
            labels_subdir = dataset_path / 'labels' / subdir
            if labels_subdir.exists():
                labels_dirs.append(labels_subdir)
        
        return labels_dirs
    
    def _find_corresponding_labels_path(self, images_path: Path, labels_paths: List[Path]) -> Optional[Path]:
        """Find the labels directory that corresponds to the given images directory."""
        
        # Extract the subdirectory name (train/val/test)
        images_parts = images_path.parts
        
        for labels_path in labels_paths:
            labels_parts = labels_path.parts
            
            # Check if they have the same subdirectory structure
            if len(images_parts) >= 2 and len(labels_parts) >= 2:
                if images_parts[-1] == labels_parts[-1]:  # Same subdirectory name
                    return labels_path
        
        # Fallback: return first labels directory if available
        return labels_paths[0] if labels_paths else None
    
    def _is_image_file(self, file_path: Path) -> bool:
        """Check if file is a valid image file."""
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
        return file_path.suffix.lower() in image_extensions
    
    async def _load_class_definitions(self, dataset_path: Path, dataset: Dataset) -> Dict[str, ClassDefinition]:
        """Load class definitions from classes.txt or data.yaml."""
        class_names = []
        
        # Try classes.txt first
        classes_file = dataset_path / 'classes.txt'
        if classes_file.exists():
            with open(classes_file, 'r') as f:
                class_names = [line.strip() for line in f.readlines() if line.strip()]
        
        # Try data.yaml if no classes.txt
        elif (dataset_path / 'data.yaml').exists():
            try:
                with open(dataset_path / 'data.yaml', 'r') as f:
                    data = yaml.safe_load(f)
                    if 'names' in data:
                        if isinstance(data['names'], dict):
                            class_names = list(data['names'].values())
                        elif isinstance(data['names'], list):
                            class_names = data['names']
            except Exception as e:
                logger.warning(f"Failed to parse data.yaml: {e}")
        
        # Create class definitions in database
        class_map = {}
        for i, name in enumerate(class_names):
            class_def = ClassDefinition(name=name, dataset_id=dataset.id)
            await class_def.insert()
            class_map[name] = class_def
            dataset.classes.append(class_def)
        
        logger.info(f"Loaded {len(class_names)} class definitions")
        return class_map
    
    async def _process_label_file(self, label_file: Path, image: Image, class_map: Dict[str, ClassDefinition]):
        """Process a single label file and create label records."""
        try:
            with open(label_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        parts = line.split()
                        if len(parts) != 5:
                            logger.warning(f"Invalid label format in {label_file}:{line_num}")
                            continue
                        
                        class_idx, x_center, y_center, width, height = parts
                        class_idx = int(class_idx)
                        
                        # Find class definition by index
                        class_def = None
                        for name, cd in class_map.items():
                            if list(class_map.keys()).index(name) == class_idx:
                                class_def = cd
                                break
                        
                        if not class_def:
                            logger.warning(f"Unknown class index {class_idx} in {label_file}:{line_num}")
                            continue
                        
                        new_label = Label(
                            class_id=class_def.id,
                            x_center=float(x_center),
                            y_center=float(y_center),
                            width=float(width),
                            height=float(height)
                        )
                        await new_label.insert()
                        image.labels.append(new_label)
                        
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse label in {label_file}:{line_num}: {e}")
                        continue
            
            await image.save()
            
        except Exception as e:
            logger.error(f"Failed to process label file {label_file}: {e}")
    
    async def _get_image_dimensions(self, image_file: Path) -> Tuple[int, int]:
        """Get image dimensions. Returns (width, height) or (0, 0) if unable to determine."""
        try:
            # This is a placeholder - in a real implementation you'd use PIL or cv2
            # For now, return placeholder values
            return (640, 480)
        except Exception:
            return (0, 0)
    
    async def _cleanup_failed_import(self, dataset: Dataset):
        """Clean up database records for a failed import."""
        try:
            # Delete associated images and labels
            images = await Image.find(Image.dataset_id == dataset.id).to_list()
            for image in images:
                # Delete labels
                labels = await Label.find(Label.id.in_([label.id for label in image.labels])).to_list()
                for label in labels:
                    await label.delete()
                # Delete image
                await image.delete()
            
            # Delete class definitions
            classes = await ClassDefinition.find(ClassDefinition.dataset_id == dataset.id).to_list()
            for class_def in classes:
                await class_def.delete()
            
            # Delete dataset
            await dataset.delete()
            
            logger.info(f"Cleaned up failed import for dataset: {dataset.name}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup dataset {dataset.name}: {e}")
    
    def _create_import_response(self, dataset: Dataset) -> dict:
        """Create a summary response for dataset import."""
        from ..schemas.dataset_schema import DatasetImportResponse
        
        metadata = dataset.metadata or {}
        
        from ..core.storage_paths import StoragePaths
        from datetime import datetime
        
        return DatasetImportResponse(
            id=str(dataset.id),
            name=dataset.name,
            description=dataset.description,
            format=dataset.format,
            file_hash=dataset.file_hash,
            processing_status=metadata.get("processing_status", "unknown"),
            images_count=metadata.get("images_count", 0),
            labels_count=metadata.get("labels_count", 0),
            processed_images=metadata.get("processed_images", 0),
            classes_count=len(dataset.classes) if hasattr(dataset, 'classes') else 0,
            original_filename=metadata.get("original_filename", ""),
            storage_path=StoragePaths.dataset_base_path(dataset.id),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

def get_yolo_import_service() -> YoloImportService:
    return YoloImportService()
