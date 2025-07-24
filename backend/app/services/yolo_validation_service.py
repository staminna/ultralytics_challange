"""
YOLO Dataset Validation Service

Extracted from YoloImportService to demonstrate Single Responsibility Principle.
This service handles ONLY validation concerns, making it:
- Testable in isolation
- Reusable across different import workflows  
- Maintainable with clear boundaries
"""

import hashlib
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from fastapi import UploadFile
from dataclasses import dataclass

from ..models.mongo_models import Dataset
from ..core.storage import get_storage_backend


@dataclass
class ValidationResult:
    """Structured validation result with detailed feedback"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    structure_info: Dict[str, any]


@dataclass
class DatasetStructure:
    """Parsed YOLO dataset structure information"""
    images_dirs: List[Path]
    labels_dirs: List[Path]
    classes_file: Optional[Path]
    data_yaml: Optional[Path]
    total_images: int
    total_labels: int


class YoloValidationService:
    """
    Focused service for YOLO dataset validation.
    
    Responsibilities:
    - Validate YOLO dataset structure
    - Check for duplicate datasets
    - Validate file formats and integrity
    - Provide detailed validation feedback
    """
    
    def __init__(self):
        self.storage = get_storage_backend()
        self.supported_image_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        self.required_structure_patterns = ['images', 'labels']
    
    def validate_dataset_structure(self, dataset_path: Path) -> ValidationResult:
        """
        Comprehensive YOLO dataset structure validation.
        
        Args:
            dataset_path: Path to extracted dataset directory
            
        Returns:
            ValidationResult with detailed feedback
        """
        errors = []
        warnings = []
        structure_info = {}
        
        try:
            # Find dataset root if nested
            root_path = self._find_dataset_root(dataset_path)
            if not root_path:
                errors.append("No valid YOLO dataset structure found")
                return ValidationResult(False, errors, warnings, structure_info)
            
            # Parse structure
            structure = self._parse_dataset_structure(root_path)
            structure_info = {
                'root_path': str(root_path),
                'images_directories': [str(p) for p in structure.images_dirs],
                'labels_directories': [str(p) for p in structure.labels_dirs],
                'total_images': structure.total_images,
                'total_labels': structure.total_labels,
                'has_classes_file': structure.classes_file is not None,
                'has_data_yaml': structure.data_yaml is not None
            }
            
            # Validate structure requirements
            if not structure.images_dirs:
                errors.append("No 'images' directory found")
            
            if not structure.labels_dirs:
                warnings.append("No 'labels' directory found - dataset has no annotations")
            
            # Validate image-label correspondence
            correspondence_errors = self._validate_image_label_correspondence(structure)
            errors.extend(correspondence_errors)
            
            # Validate file formats
            format_errors = self._validate_file_formats(structure)
            errors.extend(format_errors)
            
            # Check for empty directories
            if structure.total_images == 0:
                errors.append("No valid image files found")
            
            is_valid = len(errors) == 0
            
        except Exception as e:
            errors.append(f"Validation failed: {str(e)}")
            is_valid = False
        
        return ValidationResult(is_valid, errors, warnings, structure_info)
    
    def check_for_duplicates(self, file: UploadFile, dataset_name: str) -> Tuple[bool, Optional[str]]:
        """
        Enhanced duplicate detection with multiple criteria.
        
        Args:
            file: Uploaded file to check
            dataset_name: Proposed dataset name
            
        Returns:
            Tuple of (is_duplicate, existing_dataset_id)
        """
        try:
            # Calculate file hash for content-based duplicate detection
            file_hash = self._calculate_file_hash(file)
            
            # Check for exact name match
            name_duplicate = self._check_name_duplicate(dataset_name)
            if name_duplicate:
                return True, name_duplicate
            
            # Check for content hash match
            hash_duplicate = self._check_hash_duplicate(file_hash)
            if hash_duplicate:
                return True, hash_duplicate
            
            # Check for similar names (fuzzy matching)
            similar_duplicate = self._check_similar_names(dataset_name)
            if similar_duplicate:
                # This is a warning-level duplicate, not blocking
                return False, similar_duplicate
            
            return False, None
            
        except Exception as e:
            # Log error but don't block upload for duplicate check failures
            print(f"Duplicate check failed: {e}")
            return False, None
    
    def validate_file_formats(self, dataset_path: Path) -> List[str]:
        """
        Validate that all files in the dataset have supported formats.
        
        Args:
            dataset_path: Path to dataset directory
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        try:
            structure = self._parse_dataset_structure(dataset_path)
            
            # Check image formats
            for images_dir in structure.images_dirs:
                for image_file in images_dir.rglob('*'):
                    if image_file.is_file():
                        if not self._is_supported_image_format(image_file):
                            errors.append(f"Unsupported image format: {image_file.name}")
            
            # Check label formats (should be .txt)
            for labels_dir in structure.labels_dirs:
                for label_file in labels_dir.rglob('*.txt'):
                    if not self._is_valid_yolo_label_file(label_file):
                        errors.append(f"Invalid YOLO label format: {label_file.name}")
                        
        except Exception as e:
            errors.append(f"Format validation failed: {str(e)}")
        
        return errors
    
    # Private helper methods
    
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
    
    def _parse_dataset_structure(self, dataset_path: Path) -> DatasetStructure:
        """Parse the complete dataset structure"""
        images_dirs = self._find_images_directories(dataset_path)
        labels_dirs = self._find_labels_directories(dataset_path)
        
        # Count files
        total_images = sum(
            len([f for f in img_dir.rglob('*') if f.is_file() and self._is_supported_image_format(f)])
            for img_dir in images_dirs
        )
        
        total_labels = sum(
            len([f for f in lbl_dir.rglob('*.txt') if f.is_file()])
            for lbl_dir in labels_dirs
        )
        
        # Find metadata files
        classes_file = dataset_path / 'classes.txt' if (dataset_path / 'classes.txt').exists() else None
        data_yaml = dataset_path / 'data.yaml' if (dataset_path / 'data.yaml').exists() else None
        
        return DatasetStructure(
            images_dirs=images_dirs,
            labels_dirs=labels_dirs,
            classes_file=classes_file,
            data_yaml=data_yaml,
            total_images=total_images,
            total_labels=total_labels
        )
    
    def _find_images_directories(self, dataset_path: Path) -> List[Path]:
        """Find all directories containing images"""
        image_dirs = []
        
        # Common YOLO directory patterns
        patterns = ['images', 'train', 'val', 'test', 'valid']
        
        for pattern in patterns:
            potential_dir = dataset_path / pattern
            if potential_dir.exists() and potential_dir.is_dir():
                # Check if it contains images directly or has subdirectories with images
                if self._directory_contains_images(potential_dir):
                    image_dirs.append(potential_dir)
                else:
                    # Check subdirectories
                    for subdir in potential_dir.iterdir():
                        if subdir.is_dir() and self._directory_contains_images(subdir):
                            image_dirs.append(subdir)
        
        return image_dirs
    
    def _find_labels_directories(self, dataset_path: Path) -> List[Path]:
        """Find all directories containing label files"""
        label_dirs = []
        
        patterns = ['labels', 'annotations']
        
        for pattern in patterns:
            potential_dir = dataset_path / pattern
            if potential_dir.exists() and potential_dir.is_dir():
                if self._directory_contains_labels(potential_dir):
                    label_dirs.append(potential_dir)
                else:
                    # Check subdirectories
                    for subdir in potential_dir.iterdir():
                        if subdir.is_dir() and self._directory_contains_labels(subdir):
                            label_dirs.append(subdir)
        
        return label_dirs
    
    def _directory_contains_images(self, directory: Path) -> bool:
        """Check if directory contains image files"""
        for file in directory.iterdir():
            if file.is_file() and self._is_supported_image_format(file):
                return True
        return False
    
    def _directory_contains_labels(self, directory: Path) -> bool:
        """Check if directory contains label files"""
        return any(file.suffix == '.txt' for file in directory.iterdir() if file.is_file())
    
    def _is_supported_image_format(self, file_path: Path) -> bool:
        """Check if file has a supported image format"""
        return file_path.suffix.lower() in self.supported_image_formats
    
    def _validate_image_label_correspondence(self, structure: DatasetStructure) -> List[str]:
        """Validate that images have corresponding labels where expected"""
        errors = []
        
        # This is a simplified check - in practice, you'd implement more sophisticated logic
        if structure.total_images > 0 and structure.total_labels == 0:
            errors.append("Dataset contains images but no labels - this may be intentional for inference-only datasets")
        
        return errors
    
    def _validate_file_formats(self, structure: DatasetStructure) -> List[str]:
        """Validate file formats in the dataset"""
        errors = []
        
        # Check for corrupted or invalid files
        for images_dir in structure.images_dirs:
            for image_file in images_dir.rglob('*'):
                if image_file.is_file() and not self._is_supported_image_format(image_file):
                    errors.append(f"Unsupported image format: {image_file.name}")
        
        return errors
    
    def _calculate_file_hash(self, file: UploadFile) -> str:
        """Calculate SHA-256 hash of uploaded file"""
        hasher = hashlib.sha256()
        file.file.seek(0)
        
        while chunk := file.file.read(8192):
            hasher.update(chunk)
        
        file.file.seek(0)  # Reset file pointer
        return hasher.hexdigest()
    
    def _check_name_duplicate(self, dataset_name: str) -> Optional[str]:
        """Check for exact name duplicates"""
        # This would query your database for existing datasets
        # Simplified implementation
        return None
    
    def _check_hash_duplicate(self, file_hash: str) -> Optional[str]:
        """Check for content hash duplicates"""
        # This would query your database for existing file hashes
        # Simplified implementation
        return None
    
    def _check_similar_names(self, dataset_name: str) -> Optional[str]:
        """Check for similar dataset names using fuzzy matching"""
        # This would implement fuzzy string matching
        # Simplified implementation
        return None
    
    def _is_valid_yolo_label_file(self, label_file: Path) -> bool:
        """Validate YOLO label file format"""
        try:
            with open(label_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:  # Skip empty lines
                        parts = line.split()
                        if len(parts) != 5:  # class_id x_center y_center width height
                            return False
                        
                        # Validate numeric values
                        try:
                            class_id = int(parts[0])
                            coords = [float(x) for x in parts[1:]]
                            
                            # Validate coordinate ranges (0-1 for YOLO format)
                            if not all(0 <= coord <= 1 for coord in coords):
                                return False
                                
                        except ValueError:
                            return False
            
            return True
            
        except Exception:
            return False


def get_yolo_validation_service() -> YoloValidationService:
    """Dependency injection factory"""
    return YoloValidationService()
