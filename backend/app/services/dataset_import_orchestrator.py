"""
Dataset Import Orchestrator

Coordinates the import process by orchestrating multiple specialized services.
This replaces the monolithic YoloImportService with a focused coordinator.
"""

import hashlib
import tempfile
import zipfile
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, UploadFile, status
import logging

from ..models.mongo_models import Dataset
from ..schemas.dataset_schema import DatasetCreate
from .yolo_validation_service import YoloValidationService, get_yolo_validation_service
from .yolo_parsing_service import YoloParsingService, get_yolo_parsing_service
from .image_processing_service import ImageProcessingService, get_image_processing_service
from .dataset_service import DatasetService, get_dataset_service
from .import_cleanup_service import ImportCleanupService, get_import_cleanup_service

logger = logging.getLogger(__name__)


class DatasetImportOrchestrator:
    """
    Orchestrates the complete dataset import process.
    
    This service coordinates multiple specialized services to handle
    the complex workflow of importing YOLO datasets while maintaining
    clear separation of concerns.
    
    Responsibilities:
    - Coordinate the import workflow
    - Handle file extraction and temporary storage
    - Manage transaction-like behavior for imports
    - Provide unified error handling and logging
    """
    
    def __init__(
        self,
        validation_service: YoloValidationService = None,
        parsing_service: YoloParsingService = None,
        image_service: ImageProcessingService = None,
        dataset_service: DatasetService = None,
        cleanup_service: ImportCleanupService = None
    ):
        # Use dependency injection with defaults
        self.validation_service = validation_service or get_yolo_validation_service()
        self.parsing_service = parsing_service or get_yolo_parsing_service()
        self.image_service = image_service or get_image_processing_service()
        self.dataset_service = dataset_service or get_dataset_service()
        self.cleanup_service = cleanup_service or get_import_cleanup_service()
    
    async def import_yolo_dataset(self, file: UploadFile, dataset_name: Optional[str] = None) -> Dataset:
        """
        Import a complete YOLO dataset from an uploaded ZIP file.
        
        Args:
            file: Uploaded ZIP file containing the YOLO dataset
            dataset_name: Optional name for the dataset
            
        Returns:
            Created Dataset object
            
        Raises:
            HTTPException: For various import failures
        """
        # Use provided name or derive from filename
        if not dataset_name:
            dataset_name = Path(file.filename).stem
        
        logger.info(f"Starting import of dataset: {dataset_name}")
        
        # Step 1: Check for duplicates
        await self._check_duplicates(file, dataset_name)
        
        # Step 2: Extract and validate the dataset
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            try:
                # Extract the uploaded file
                dataset_path = await self._extract_dataset(file, temp_path)
                
                # Validate the dataset structure
                validation_result = self.validation_service.validate_dataset_structure(dataset_path)
                if not validation_result.is_valid:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid YOLO dataset: {'; '.join(validation_result.errors)}"
                    )
                
                # Step 3: Create the dataset record
                dataset = await self._create_dataset_record(dataset_name, file, validation_result)
                
                # Step 4: Process the dataset content
                await self._process_dataset_content(dataset_path, dataset)
                
                logger.info(f"Successfully imported dataset: {dataset_name}")
                return dataset
                
            except Exception as e:
                logger.error(f"Import failed for dataset {dataset_name}: {e}")
                # Cleanup will be handled by the context manager and service
                raise
    
    async def get_import_status(self, dataset_id: str) -> dict:
        """
        Get the status of a dataset import.
        
        Args:
            dataset_id: ID of the dataset being imported
            
        Returns:
            Dictionary containing import status information
        """
        try:
            dataset = await self.dataset_service.get_dataset(dataset_id)
            if not dataset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dataset not found"
                )
            
            # Get processing statistics
            images_count = len(dataset.images) if dataset.images else 0
            labels_count = sum(len(img.labels) for img in dataset.images if img.labels) if dataset.images else 0
            
            return {
                'dataset_id': str(dataset.id),
                'name': dataset.name,
                'status': 'completed',  # Simplified - could be enhanced with actual status tracking
                'images_processed': images_count,
                'labels_processed': labels_count,
                'created_at': dataset.created_at.isoformat() if dataset.created_at else None
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting import status for {dataset_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error retrieving import status"
            )
    
    # Private orchestration methods
    
    async def _check_duplicates(self, file: UploadFile, dataset_name: str) -> None:
        """Check for duplicate datasets"""
        is_duplicate, existing_id = self.validation_service.check_for_duplicates(file, dataset_name)
        if is_duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Dataset already exists with ID: {existing_id}"
            )
    
    async def _extract_dataset(self, file: UploadFile, temp_path: Path) -> Path:
        """Extract the uploaded ZIP file and find the dataset root"""
        zip_path = temp_path / file.filename
        
        # Save uploaded file
        logger.info("Extracting uploaded dataset...")
        with open(zip_path, "wb") as buffer:
            chunk_size = 8192  # 8KB chunks
            while chunk := await file.read(chunk_size):
                buffer.write(chunk)
        
        # Extract ZIP file
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_path)
            logger.info("Successfully extracted ZIP file")
        except zipfile.BadZipFile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ZIP file"
            )
        
        # Find the dataset root directory
        dataset_path = self._find_dataset_root(temp_path)
        if not dataset_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid YOLO dataset structure found in ZIP file"
            )
        
        return dataset_path
    
    async def _create_dataset_record(self, dataset_name: str, file: UploadFile, validation_result) -> Dataset:
        """Create the initial dataset record in the database"""
        # Calculate file hash for integrity
        file_size = len(await file.read())
        await file.seek(0)  # Reset file pointer
        
        file_hash = "large_file" if file_size > 100 * 1024 * 1024 else self._calculate_file_hash(file)
        
        # Create dataset
        dataset_create = DatasetCreate(
            name=dataset_name,
            description=f"Imported YOLO dataset from {file.filename}",
            format="yolo",
            file_hash=file_hash
        )
        
        dataset = await self.dataset_service.create_dataset(dataset_create)
        logger.info(f"Created dataset record with ID: {dataset.id}")
        
        return dataset
    
    async def _process_dataset_content(self, dataset_path: Path, dataset: Dataset) -> None:
        """Process the dataset content (images, labels, classes)"""
        try:
            # Parse the dataset structure
            structure = self.parsing_service.parse_dataset_structure(dataset_path)
            
            # Load class definitions
            class_map = self.parsing_service.load_class_definitions(dataset_path, dataset)
            
            # Save class definitions to database
            for class_def in class_map.values():
                await class_def.save()
            
            # Process images and labels
            await self._process_images_and_labels(structure, dataset, class_map)
            
            logger.info(f"Processed {structure['total_images']} images and {structure['total_labels']} labels")
            
        except Exception as e:
            logger.error(f"Error processing dataset content: {e}")
            # Cleanup partial import
            await self.cleanup_service.cleanup_failed_import(dataset)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing dataset content: {str(e)}"
            )
    
    async def _process_images_and_labels(self, structure: dict, dataset: Dataset, class_map: dict) -> None:
        """Process all images and their corresponding labels"""
        processed_count = 0
        
        for images_dir in structure['images_directories']:
            for image_path in images_dir.rglob('*'):
                if not image_path.is_file():
                    continue
                
                # Validate and process image
                is_valid, error_msg = self.image_service.validate_image_file(image_path)
                if not is_valid:
                    logger.warning(f"Skipping invalid image {image_path}: {error_msg}")
                    continue
                
                # Create image record
                image_metadata = self.image_service.get_image_metadata(image_path)
                image = await self._create_image_record(image_metadata, dataset.id)
                
                # Store the image file
                if not self.image_service.store_image(image_path, image):
                    logger.warning(f"Failed to store image: {image.file_name}")
                    continue
                
                # Process corresponding labels
                label_file = self.image_service.find_corresponding_label_file(
                    image_path, structure['labels_directories']
                )
                
                if label_file:
                    labels = self.parsing_service.parse_label_file(label_file, image, class_map)
                    for label in labels:
                        await label.save()
                
                # Save the image record
                await image.save()
                processed_count += 1
                
                # Log progress for large datasets
                if processed_count % 100 == 0:
                    logger.info(f"Processed {processed_count} images...")
    
    async def _create_image_record(self, metadata: dict, dataset_id: str):
        """Create an Image record from metadata"""
        from ..models.mongo_models import Image
        
        return Image(
            dataset_id=dataset_id,
            file_name=metadata['filename'],
            gcs_path="",  # Will be set later when uploaded to storage
            width=metadata['width'],
            height=metadata['height']
        )
    
    def _find_dataset_root(self, temp_path: Path) -> Optional[Path]:
        """Find the root directory of the YOLO dataset"""
        # Check if current directory is already the root
        if self._is_yolo_dataset_root(temp_path):
            return temp_path
        
        # Search subdirectories for YOLO structure
        for subdir in temp_path.rglob('*'):
            if subdir.is_dir() and self._is_yolo_dataset_root(subdir):
                return subdir
        
        return None
    
    def _is_yolo_dataset_root(self, path: Path) -> bool:
        """Check if a directory contains YOLO dataset structure"""
        has_images = any((path / pattern).exists() for pattern in ['images', 'train', 'val', 'test'])
        return has_images
    
    def _calculate_file_hash(self, file: UploadFile) -> str:
        """Calculate SHA-256 hash of uploaded file"""
        hasher = hashlib.sha256()
        file.file.seek(0)
        
        while chunk := file.file.read(8192):
            hasher.update(chunk)
        
        file.file.seek(0)  # Reset file pointer
        return hasher.hexdigest()


def get_dataset_import_orchestrator() -> DatasetImportOrchestrator:
    """Dependency injection factory"""
    return DatasetImportOrchestrator()
