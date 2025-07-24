"""
YOLO Dataset Parsing Service

Handles parsing of YOLO dataset structures, class definitions, and label files.
Extracted from YoloImportService for better separation of concerns.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image as PILImage
import logging

from ..models.mongo_models import Dataset, Image, Label, ClassDefinition

logger = logging.getLogger(__name__)


class YoloParsingService:
    """
    Service responsible for parsing YOLO dataset structures and content.
    
    Responsibilities:
    - Parse dataset directory structure
    - Load class definitions from files
    - Parse individual label files
    - Extract image metadata
    """
    
    def __init__(self):
        self.supported_image_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    
    def parse_dataset_structure(self, dataset_path: Path) -> Dict[str, any]:
        """
        Parse the complete YOLO dataset structure.
        
        Args:
            dataset_path: Path to the dataset root directory
            
        Returns:
            Dictionary containing parsed structure information
        """
        logger.info(f"Parsing dataset structure at: {dataset_path}")
        
        structure = {
            'images_directories': self._find_images_directories(dataset_path),
            'labels_directories': self._find_labels_directories(dataset_path),
            'classes_file': self._find_classes_file(dataset_path),
            'data_yaml': self._find_data_yaml(dataset_path),
            'total_images': 0,
            'total_labels': 0
        }
        
        # Count files
        structure['total_images'] = self._count_images(structure['images_directories'])
        structure['total_labels'] = self._count_labels(structure['labels_directories'])
        
        logger.info(f"Found {structure['total_images']} images and {structure['total_labels']} labels")
        
        return structure
    
    def load_class_definitions(self, dataset_path: Path, dataset: Dataset) -> Dict[str, ClassDefinition]:
        """
        Load class definitions from classes.txt or data.yaml file.
        
        Args:
            dataset_path: Path to dataset directory
            dataset: Dataset model to associate classes with
            
        Returns:
            Dictionary mapping class names to ClassDefinition objects
        """
        logger.info("Loading class definitions...")
        
        class_map = {}
        
        # Try to load from data.yaml first
        data_yaml_path = dataset_path / 'data.yaml'
        if data_yaml_path.exists():
            class_map = self._load_classes_from_yaml(data_yaml_path, dataset)
        
        # Fallback to classes.txt
        if not class_map:
            classes_txt_path = dataset_path / 'classes.txt'
            if classes_txt_path.exists():
                class_map = self._load_classes_from_txt(classes_txt_path, dataset)
        
        # Create default classes if none found
        if not class_map:
            logger.warning("No class definitions found, using default 'object' class")
            class_def = ClassDefinition(
                name="object",
                class_id=0,
                dataset_id=dataset.id
            )
            class_map["object"] = class_def
        
        logger.info(f"Loaded {len(class_map)} class definitions")
        return class_map
    
    def parse_label_file(self, label_file: Path, image: Image, class_map: Dict[str, ClassDefinition]) -> List[Label]:
        """
        Parse a YOLO format label file and create Label objects.
        
        Args:
            label_file: Path to the .txt label file
            image: Image object the labels belong to
            class_map: Dictionary of class definitions
            
        Returns:
            List of Label objects
        """
        labels = []
        
        try:
            with open(label_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:  # Skip empty lines
                        continue
                    
                    try:
                        parts = line.split()
                        if len(parts) != 5:
                            logger.warning(f"Invalid label format in {label_file}:{line_num}")
                            continue
                        
                        class_id = int(parts[0])
                        x_center = float(parts[1])
                        y_center = float(parts[2])
                        width = float(parts[3])
                        height = float(parts[4])
                        
                        # Validate coordinate ranges
                        if not all(0 <= coord <= 1 for coord in [x_center, y_center, width, height]):
                            logger.warning(f"Invalid coordinates in {label_file}:{line_num}")
                            continue
                        
                        # Find class definition
                        class_def = self._find_class_by_id(class_id, class_map)
                        if not class_def:
                            logger.warning(f"Unknown class ID {class_id} in {label_file}:{line_num}")
                            continue
                        
                        # Create label
                        label = Label(
                            image_id=image.id,
                            class_id=class_def.class_id,
                            x_center=x_center,
                            y_center=y_center,
                            width=width,
                            height=height
                        )
                        labels.append(label)
                        
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Error parsing line {line_num} in {label_file}: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Error reading label file {label_file}: {e}")
        
        return labels
    
    def get_image_dimensions(self, image_path: Path) -> Tuple[int, int]:
        """
        Get image dimensions using PIL.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple of (width, height) or (0, 0) if unable to determine
        """
        try:
            with PILImage.open(image_path) as img:
                return img.size
        except Exception as e:
            logger.warning(f"Could not get dimensions for {image_path}: {e}")
            return (0, 0)
    
    # Private helper methods
    
    def _find_images_directories(self, dataset_path: Path) -> List[Path]:
        """Find all directories containing images"""
        image_dirs = []
        patterns = ['images', 'train', 'val', 'test', 'valid']
        
        for pattern in patterns:
            potential_dir = dataset_path / pattern
            if potential_dir.exists() and potential_dir.is_dir():
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
    
    def _find_classes_file(self, dataset_path: Path) -> Optional[Path]:
        """Find classes.txt file"""
        classes_file = dataset_path / 'classes.txt'
        return classes_file if classes_file.exists() else None
    
    def _find_data_yaml(self, dataset_path: Path) -> Optional[Path]:
        """Find data.yaml file"""
        data_yaml = dataset_path / 'data.yaml'
        return data_yaml if data_yaml.exists() else None
    
    def _directory_contains_images(self, directory: Path) -> bool:
        """Check if directory contains image files"""
        for file in directory.iterdir():
            if file.is_file() and file.suffix.lower() in self.supported_image_formats:
                return True
        return False
    
    def _directory_contains_labels(self, directory: Path) -> bool:
        """Check if directory contains label files"""
        return any(file.suffix == '.txt' for file in directory.iterdir() if file.is_file())
    
    def _count_images(self, image_dirs: List[Path]) -> int:
        """Count total number of image files"""
        total = 0
        for img_dir in image_dirs:
            for file in img_dir.rglob('*'):
                if file.is_file() and file.suffix.lower() in self.supported_image_formats:
                    total += 1
        return total
    
    def _count_labels(self, label_dirs: List[Path]) -> int:
        """Count total number of label files"""
        total = 0
        for lbl_dir in label_dirs:
            for file in lbl_dir.rglob('*.txt'):
                if file.is_file():
                    total += 1
        return total
    
    def _load_classes_from_yaml(self, yaml_path: Path, dataset: Dataset) -> Dict[str, ClassDefinition]:
        """Load class definitions from data.yaml file"""
        class_map = {}
        
        try:
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)
            
            if 'names' in data:
                names = data['names']
                if isinstance(names, dict):
                    # Format: {0: 'person', 1: 'bicycle', ...}
                    for class_id, class_name in names.items():
                        class_def = ClassDefinition(
                            name=str(class_name),
                            class_id=int(class_id),
                            dataset_id=dataset.id
                        )
                        class_map[str(class_name)] = class_def
                elif isinstance(names, list):
                    # Format: ['person', 'bicycle', ...]
                    for class_id, class_name in enumerate(names):
                        class_def = ClassDefinition(
                            name=str(class_name),
                            class_id=class_id,
                            dataset_id=dataset.id
                        )
                        class_map[str(class_name)] = class_def
        
        except Exception as e:
            logger.error(f"Error loading classes from YAML {yaml_path}: {e}")
        
        return class_map
    
    def _load_classes_from_txt(self, txt_path: Path, dataset: Dataset) -> Dict[str, ClassDefinition]:
        """Load class definitions from classes.txt file"""
        class_map = {}
        
        try:
            with open(txt_path, 'r') as f:
                for class_id, line in enumerate(f):
                    class_name = line.strip()
                    if class_name:
                        class_def = ClassDefinition(
                            name=class_name,
                            class_id=class_id,
                            dataset_id=dataset.id
                        )
                        class_map[class_name] = class_def
        
        except Exception as e:
            logger.error(f"Error loading classes from TXT {txt_path}: {e}")
        
        return class_map
    
    def _find_class_by_id(self, class_id: int, class_map: Dict[str, ClassDefinition]) -> Optional[ClassDefinition]:
        """Find class definition by ID"""
        for class_def in class_map.values():
            if class_def.class_id == class_id:
                return class_def
        return None


def get_yolo_parsing_service() -> YoloParsingService:
    """Dependency injection factory"""
    return YoloParsingService()
