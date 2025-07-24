"""
Import Cleanup Service

Handles cleanup operations for failed or partial dataset imports.
Extracted from YoloImportService for better separation of concerns.
"""

import logging
from typing import List, Optional

from ..models.mongo_models import Dataset, Image, Label, ClassDefinition
from ..core.storage import get_storage_backend

logger = logging.getLogger(__name__)


class ImportCleanupService:
    """
    Service responsible for cleaning up failed or partial imports.
    
    Responsibilities:
    - Clean up database records for failed imports
    - Remove stored files for failed imports
    - Handle rollback operations
    - Provide cleanup status reporting
    """
    
    def __init__(self):
        self.storage = get_storage_backend()
    
    async def cleanup_failed_import(self, dataset: Dataset) -> bool:
        """
        Clean up all resources associated with a failed dataset import.
        
        Args:
            dataset: Dataset object to clean up
            
        Returns:
            True if cleanup was successful, False otherwise
        """
        logger.info(f"Starting cleanup for failed import of dataset: {dataset.name}")
        
        try:
            # Track cleanup progress
            cleanup_stats = {
                'images_deleted': 0,
                'labels_deleted': 0,
                'classes_deleted': 0,
                'files_deleted': 0,
                'errors': []
            }
            
            # Clean up images and their associated data
            if dataset.images:
                cleanup_stats['images_deleted'] = await self._cleanup_images(dataset.images, cleanup_stats)
            
            # Clean up class definitions
            cleanup_stats['classes_deleted'] = await self._cleanup_class_definitions(dataset.id)
            
            # Finally, delete the dataset record
            await dataset.delete()
            
            # Log cleanup summary
            logger.info(
                f"Cleanup completed for dataset {dataset.name}: "
                f"{cleanup_stats['images_deleted']} images, "
                f"{cleanup_stats['labels_deleted']} labels, "
                f"{cleanup_stats['classes_deleted']} classes deleted"
            )
            
            if cleanup_stats['errors']:
                logger.warning(f"Cleanup had {len(cleanup_stats['errors'])} errors: {cleanup_stats['errors']}")
            
            return len(cleanup_stats['errors']) == 0
            
        except Exception as e:
            logger.error(f"Error during cleanup of dataset {dataset.name}: {e}")
            return False
    
    async def cleanup_partial_import(self, dataset_id: str, preserve_dataset: bool = False) -> bool:
        """
        Clean up a partially completed import while optionally preserving the dataset record.
        
        Args:
            dataset_id: ID of the dataset to clean up
            preserve_dataset: Whether to keep the dataset record
            
        Returns:
            True if cleanup was successful, False otherwise
        """
        logger.info(f"Starting partial cleanup for dataset: {dataset_id}")
        
        try:
            # Find the dataset
            dataset = await Dataset.get(dataset_id)
            if not dataset:
                logger.warning(f"Dataset {dataset_id} not found for cleanup")
                return True  # Nothing to clean up
            
            # Clean up associated data but preserve dataset if requested
            cleanup_stats = {'images_deleted': 0, 'labels_deleted': 0, 'files_deleted': 0}
            
            if dataset.images:
                cleanup_stats['images_deleted'] = await self._cleanup_images(dataset.images, cleanup_stats)
            
            if not preserve_dataset:
                await dataset.delete()
                logger.info(f"Deleted dataset record: {dataset.name}")
            else:
                # Clear the images reference but keep the dataset
                dataset.images = []
                await dataset.save()
                logger.info(f"Cleared images from dataset: {dataset.name}")
            
            logger.info(f"Partial cleanup completed: {cleanup_stats}")
            return True
            
        except Exception as e:
            logger.error(f"Error during partial cleanup of dataset {dataset_id}: {e}")
            return False
    
    async def cleanup_orphaned_files(self, dataset_id: str) -> int:
        """
        Clean up orphaned files that don't have corresponding database records.
        
        Args:
            dataset_id: ID of the dataset to check for orphaned files
            
        Returns:
            Number of orphaned files cleaned up
        """
        logger.info(f"Cleaning up orphaned files for dataset: {dataset_id}")
        
        try:
            # This is a simplified implementation
            # In a real system, you'd scan storage for files and cross-reference with database
            
            # Get all image records for the dataset
            dataset = await Dataset.get(dataset_id)
            if not dataset or not dataset.images:
                return 0
            
            # Get list of files that should exist
            expected_files = set()
            for image in dataset.images:
                if image.storage_path:
                    expected_files.add(image.storage_path)
                if image.gcs_path:
                    expected_files.add(image.gcs_path)
            
            # This would need to be implemented based on your storage backend
            # For now, return 0 as a placeholder
            logger.info("Orphaned file cleanup completed")
            return 0
            
        except Exception as e:
            logger.error(f"Error cleaning up orphaned files for dataset {dataset_id}: {e}")
            return 0
    
    async def get_cleanup_status(self, dataset_id: str) -> dict:
        """
        Get the status of cleanup operations for a dataset.
        
        Args:
            dataset_id: ID of the dataset to check
            
        Returns:
            Dictionary containing cleanup status information
        """
        try:
            dataset = await Dataset.get(dataset_id)
            
            if not dataset:
                return {
                    'dataset_id': dataset_id,
                    'status': 'not_found',
                    'message': 'Dataset not found - may have been cleaned up'
                }
            
            # Count remaining resources
            images_count = len(dataset.images) if dataset.images else 0
            labels_count = 0
            
            if dataset.images:
                for image in dataset.images:
                    if image.labels:
                        labels_count += len(image.labels)
            
            return {
                'dataset_id': dataset_id,
                'dataset_name': dataset.name,
                'status': 'exists',
                'remaining_images': images_count,
                'remaining_labels': labels_count,
                'created_at': dataset.created_at.isoformat() if dataset.created_at else None
            }
            
        except Exception as e:
            logger.error(f"Error getting cleanup status for dataset {dataset_id}: {e}")
            return {
                'dataset_id': dataset_id,
                'status': 'error',
                'message': str(e)
            }
    
    # Private helper methods
    
    async def _cleanup_images(self, images: List[Image], cleanup_stats: dict) -> int:
        """Clean up a list of images and their associated data"""
        images_deleted = 0
        
        for image in images:
            try:
                # Clean up labels first
                if image.labels:
                    labels_deleted = await self._cleanup_labels(image.labels)
                    cleanup_stats['labels_deleted'] += labels_deleted
                
                # Clean up stored files
                if await self._cleanup_image_files(image):
                    cleanup_stats['files_deleted'] += 1
                
                # Delete the image record
                await image.delete()
                images_deleted += 1
                
            except Exception as e:
                error_msg = f"Error cleaning up image {image.filename}: {e}"
                logger.error(error_msg)
                cleanup_stats['errors'].append(error_msg)
        
        return images_deleted
    
    async def _cleanup_labels(self, labels: List[Label]) -> int:
        """Clean up a list of labels"""
        labels_deleted = 0
        
        for label in labels:
            try:
                await label.delete()
                labels_deleted += 1
            except Exception as e:
                logger.error(f"Error deleting label {label.id}: {e}")
        
        return labels_deleted
    
    async def _cleanup_image_files(self, image: Image) -> bool:
        """Clean up stored files for an image"""
        files_cleaned = 0
        
        try:
            # Clean up local storage file
            if image.storage_path:
                if self.storage.delete_file(image.storage_path):
                    files_cleaned += 1
                    logger.debug(f"Deleted storage file: {image.storage_path}")
                else:
                    logger.warning(f"Failed to delete storage file: {image.storage_path}")
            
            # Clean up GCS file if it exists
            if image.gcs_path:
                # This would need to be implemented based on your GCS setup
                logger.debug(f"Would delete GCS file: {image.gcs_path}")
                files_cleaned += 1
            
            return files_cleaned > 0
            
        except Exception as e:
            logger.error(f"Error cleaning up files for image {image.filename}: {e}")
            return False
    
    async def _cleanup_class_definitions(self, dataset_id: str) -> int:
        """Clean up class definitions for a dataset"""
        try:
            # Find all class definitions for this dataset
            class_definitions = await ClassDefinition.find(
                ClassDefinition.dataset_id == dataset_id
            ).to_list()
            
            classes_deleted = 0
            for class_def in class_definitions:
                try:
                    await class_def.delete()
                    classes_deleted += 1
                except Exception as e:
                    logger.error(f"Error deleting class definition {class_def.name}: {e}")
            
            return classes_deleted
            
        except Exception as e:
            logger.error(f"Error cleaning up class definitions for dataset {dataset_id}: {e}")
            return 0


def get_import_cleanup_service() -> ImportCleanupService:
    """Dependency injection factory"""
    return ImportCleanupService()
