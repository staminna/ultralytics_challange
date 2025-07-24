"""
Image Processing Service

Handles image validation, processing, and storage operations.
Extracted from YoloImportService for better separation of concerns.
"""

import hashlib
from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image as PILImage
import logging

from ..models.mongo_models import Image
from ..core.storage import get_storage_backend

logger = logging.getLogger(__name__)


class ImageProcessingService:
    """
    Service responsible for image processing and validation.
    
    Responsibilities:
    - Validate image files and formats
    - Process images and extract metadata
    - Handle image storage operations
    - Generate image hashes for deduplication
    """
    
    def __init__(self):
        self.storage = get_storage_backend()
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        self.max_image_size = 50 * 1024 * 1024  # 50MB per image
    
    def validate_image_file(self, image_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate an image file for format, size, and integrity.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check file extension
            if image_path.suffix.lower() not in self.supported_formats:
                return False, f"Unsupported image format: {image_path.suffix}"
            
            # Check file size
            file_size = image_path.stat().st_size
            if file_size > self.max_image_size:
                return False, f"Image too large: {file_size / (1024*1024):.1f}MB (max: 50MB)"
            
            # Check if file can be opened as image
            try:
                with PILImage.open(image_path) as img:
                    # Verify image can be loaded
                    img.verify()
                return True, None
                
            except Exception as e:
                return False, f"Corrupted image file: {str(e)}"
        
        except Exception as e:
            return False, f"Error validating image: {str(e)}"
    
    def get_image_metadata(self, image_path: Path) -> dict:
        """
        Extract metadata from an image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing image metadata
        """
        metadata = {
            'filename': image_path.name,
            'width': 0,
            'height': 0,
            'format': None,
            'size_bytes': 0,
            'hash': None
        }
        
        try:
            # Get file size
            metadata['size_bytes'] = image_path.stat().st_size
            
            # Get image dimensions and format
            with PILImage.open(image_path) as img:
                metadata['width'], metadata['height'] = img.size
                metadata['format'] = img.format
            
            # Calculate file hash
            metadata['hash'] = self._calculate_file_hash(image_path)
            
        except Exception as e:
            logger.warning(f"Error extracting metadata from {image_path}: {e}")
        
        return metadata
    
    def process_image_batch(self, image_paths: List[Path], dataset_id: str) -> List[Image]:
        """
        Process a batch of images and create Image objects.
        
        Args:
            image_paths: List of paths to image files
            dataset_id: ID of the dataset the images belong to
            
        Returns:
            List of processed Image objects
        """
        logger.info(f"Processing batch of {len(image_paths)} images")
        
        processed_images = []
        
        for image_path in image_paths:
            try:
                # Validate image
                is_valid, error_msg = self.validate_image_file(image_path)
                if not is_valid:
                    logger.warning(f"Skipping invalid image {image_path}: {error_msg}")
                    continue
                
                # Extract metadata
                metadata = self.get_image_metadata(image_path)
                
                # Create Image object
                image = Image(
                    dataset_id=dataset_id,
                    filename=metadata['filename'],
                    width=metadata['width'],
                    height=metadata['height'],
                    file_size=metadata['size_bytes'],
                    file_hash=metadata['hash'],
                    storage_path=None,  # Will be set when stored
                    gcs_path=None       # Will be set when uploaded to GCS
                )
                
                processed_images.append(image)
                
            except Exception as e:
                logger.error(f"Error processing image {image_path}: {e}")
                continue
        
        logger.info(f"Successfully processed {len(processed_images)} images")
        return processed_images
    
    def store_image(self, image_path: Path, image: Image) -> bool:
        """
        Store an image file using the configured storage backend.
        
        Args:
            image_path: Path to the source image file
            image: Image object to update with storage information
            
        Returns:
            True if storage was successful, False otherwise
        """
        try:
            # Generate storage path
            storage_path = f"datasets/{image.dataset_id}/images/{image.filename}"
            
            # Store using the storage backend
            success = self.storage.store_file(image_path, storage_path)
            
            if success:
                image.storage_path = storage_path
                logger.debug(f"Stored image {image.filename} at {storage_path}")
                return True
            else:
                logger.error(f"Failed to store image {image.filename}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing image {image.filename}: {e}")
            return False
    
    def find_corresponding_label_file(self, image_path: Path, labels_directories: List[Path]) -> Optional[Path]:
        """
        Find the corresponding label file for an image.
        
        Args:
            image_path: Path to the image file
            labels_directories: List of directories that might contain labels
            
        Returns:
            Path to the corresponding label file, or None if not found
        """
        # Get image filename without extension
        image_stem = image_path.stem
        
        for labels_dir in labels_directories:
            # Check if labels directory corresponds to images directory
            if self._directories_correspond(image_path.parent, labels_dir):
                label_path = labels_dir / f"{image_stem}.txt"
                if label_path.exists():
                    return label_path
        
        return None
    
    def deduplicate_images(self, images: List[Image]) -> List[Image]:
        """
        Remove duplicate images based on file hash.
        
        Args:
            images: List of Image objects to deduplicate
            
        Returns:
            List of unique Image objects
        """
        seen_hashes = set()
        unique_images = []
        
        for image in images:
            if image.file_hash and image.file_hash not in seen_hashes:
                seen_hashes.add(image.file_hash)
                unique_images.append(image)
            elif not image.file_hash:
                # Keep images without hashes (shouldn't happen in normal flow)
                unique_images.append(image)
            else:
                logger.info(f"Removing duplicate image: {image.filename}")
        
        if len(unique_images) != len(images):
            logger.info(f"Removed {len(images) - len(unique_images)} duplicate images")
        
        return unique_images
    
    # Private helper methods
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file"""
        hasher = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.warning(f"Error calculating hash for {file_path}: {e}")
            return ""
    
    def _directories_correspond(self, images_dir: Path, labels_dir: Path) -> bool:
        """
        Check if an images directory corresponds to a labels directory.
        
        This uses heuristics to match directories like:
        - images/train -> labels/train
        - train/images -> train/labels
        """
        # Extract the last part of the path for comparison
        images_parts = images_dir.parts
        labels_parts = labels_dir.parts
        
        # Simple heuristic: if they have the same parent or similar structure
        if len(images_parts) >= 2 and len(labels_parts) >= 2:
            # Check if they share a common parent structure
            if images_parts[-2] == labels_parts[-2]:  # Same parent directory
                return True
            
            # Check for train/val/test correspondence
            common_splits = {'train', 'val', 'test', 'valid'}
            images_split = None
            labels_split = None
            
            for part in images_parts:
                if part in common_splits:
                    images_split = part
                    break
            
            for part in labels_parts:
                if part in common_splits:
                    labels_split = part
                    break
            
            if images_split and labels_split and images_split == labels_split:
                return True
        
        # Default: assume they correspond if we can't determine otherwise
        return True


def get_image_processing_service() -> ImageProcessingService:
    """Dependency injection factory"""
    return ImageProcessingService()
