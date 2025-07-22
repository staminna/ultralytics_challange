#!/usr/bin/env python3
"""
Furniture Classifier for YOLO Dataset
This script analyzes hotel images and their bounding boxes to better classify furniture types
based on visual characteristics and aspect ratios.
"""

import os
import json
import argparse
import requests
import logging
from pathlib import Path
from PIL import Image
from io import BytesIO
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constants
API_BASE_URL = "http://localhost:8000/api/v1"
TIMEOUT = 30  # seconds
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
CONFIG_FILE = OUTPUT_DIR / "furniture_config.json"

# Furniture classification based on aspect ratio and size
FURNITURE_TYPES = [
    # Format: (min_aspect_ratio, max_aspect_ratio, min_rel_size, max_rel_size, furniture_type)
    # Aspect ratio = width/height
    (0.8, 1.5, 0.05, 0.15, "chair"),      # Square-ish, small
    (1.5, 3.0, 0.05, 0.2, "bench"),       # Wide, small
    (0.8, 1.5, 0.15, 0.3, "table"),       # Square-ish, medium
    (1.5, 3.0, 0.15, 0.4, "sofa"),        # Wide, medium
    (0.5, 0.8, 0.1, 0.3, "cabinet"),      # Tall, medium
    (0.8, 2.0, 0.3, 1.0, "bed"),          # Large furniture
]

# Default fallbacks by class ID
DEFAULT_CLASS_MAPPINGS = {
    0: "bed",
    1: "chair",
    2: "table"
}

class FurnitureClassifier:
    """Class to classify furniture in hotel images based on visual characteristics."""
    
    def __init__(self, api_url: str = API_BASE_URL, timeout: int = TIMEOUT):
        """Initialize the FurnitureClassifier."""
        self.api_url = api_url
        self.timeout = timeout
        self.config = self.load_config()
        
    def check_server_health(self) -> bool:
        """Check if the server is healthy."""
        try:
            logger.info("Checking server health...")
            response = requests.get(f"{self.api_url}/health", timeout=self.timeout)
            if response.status_code == 200:
                logger.info("✅ Server is healthy")
                return True
            else:
                logger.error(f"❌ Server health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Server health check failed: {str(e)}")
            return False
    
    def get_datasets(self) -> List[Dict[str, Any]]:
        """Get a list of all datasets."""
        try:
            logger.info("Retrieving datasets...")
            response = requests.get(f"{self.api_url}/datasets/", timeout=self.timeout)
            if response.status_code == 200:
                # Handle the API response format
                data = response.json()
                if isinstance(data, dict) and 'datasets' in data:
                    datasets = data['datasets']
                else:
                    datasets = data
                    
                logger.info(f"✅ Retrieved {len(datasets)} datasets")
                return datasets
            else:
                logger.error(f"❌ Failed to retrieve datasets: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"❌ Failed to retrieve datasets: {str(e)}")
            return []
    
    def get_dataset_details(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific dataset."""
        try:
            logger.info(f"Retrieving details for dataset {dataset_id}...")
            response = requests.get(f"{self.api_url}/datasets/{dataset_id}", timeout=self.timeout)
            if response.status_code == 200:
                dataset = response.json()
                logger.info(f"✅ Retrieved details for dataset {dataset_id}")
                return dataset
            else:
                logger.error(f"❌ Failed to retrieve dataset details: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to retrieve dataset details: {str(e)}")
            return None
    
    def get_dataset_images(self, dataset_id: str, limit: int = 100, with_labels: bool = True) -> List[Dict[str, Any]]:
        """Get images with labels for a dataset."""
        try:
            logger.info(f"Retrieving images for dataset {dataset_id}...")
            params = {"limit": limit}
            if with_labels:
                params["with_labels"] = "true"
                
            response = requests.get(
                f"{self.api_url}/datasets/{dataset_id}/images",
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                images = data.get('images', [])
                total = data.get('total', 0)
                logger.info(f"✅ Retrieved {len(images)} of {total} images for dataset {dataset_id}")
                return images
            else:
                logger.error(f"❌ Failed to retrieve images: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"❌ Failed to retrieve images: {str(e)}")
            return []
    
    def download_image(self, url: str) -> Optional[Image.Image]:
        """Download an image from a URL."""
        try:
            response = requests.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return Image.open(BytesIO(response.content))
            else:
                logger.error(f"❌ Failed to download image: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to download image: {str(e)}")
            return None

class FurnitureClassifier:
    """Class to classify furniture in hotel images based on visual characteristics."""
    
    def __init__(self, api_url: str = API_BASE_URL, timeout: int = TIMEOUT):
        """Initialize the FurnitureClassifier."""
        self.api_url = api_url
        self.timeout = timeout
        self.config = self.load_config()
        
    def check_server_health(self) -> bool:
        """Check if the server is healthy."""
        try:
            logger.info("Checking server health...")
            response = requests.get(f"{self.api_url}/health", timeout=self.timeout)
            if response.status_code == 200:
                logger.info("✅ Server is healthy")
                return True
            else:
                logger.error(f"❌ Server health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Server health check failed: {str(e)}")
            return False
    
    def get_datasets(self) -> List[Dict[str, Any]]:
        """Get a list of all datasets."""
        try:
            logger.info("Retrieving datasets...")
            response = requests.get(f"{self.api_url}/datasets/", timeout=self.timeout)
            if response.status_code == 200:
                # Handle the API response format
                data = response.json()
                if isinstance(data, dict) and 'datasets' in data:
                    datasets = data['datasets']
                else:
                    datasets = data
                    
                logger.info(f"✅ Retrieved {len(datasets)} datasets")
                return datasets
            else:
                logger.error(f"❌ Failed to retrieve datasets: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"❌ Failed to retrieve datasets: {str(e)}")
            return []
    
    def get_dataset_details(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific dataset."""
        try:
            logger.info(f"Retrieving details for dataset {dataset_id}...")
            response = requests.get(f"{self.api_url}/datasets/{dataset_id}", timeout=self.timeout)
            if response.status_code == 200:
                dataset = response.json()
                logger.info(f"✅ Retrieved details for dataset {dataset_id}")
                return dataset
            else:
                logger.error(f"❌ Failed to retrieve dataset details: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to retrieve dataset details: {str(e)}")
            return None
    
    def get_dataset_images(self, dataset_id: str, limit: int = 100, with_labels: bool = True) -> List[Dict[str, Any]]:
        """Get images with labels for a dataset."""
        try:
            logger.info(f"Retrieving images for dataset {dataset_id}...")
            params = {"limit": limit}
            if with_labels:
                params["with_labels"] = "true"
                
            response = requests.get(
                f"{self.api_url}/datasets/{dataset_id}/images",
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                images = data.get('images', [])
                total = data.get('total', 0)
                logger.info(f"✅ Retrieved {len(images)} of {total} images for dataset {dataset_id}")
                return images
            else:
                logger.error(f"❌ Failed to retrieve images: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"❌ Failed to retrieve images: {str(e)}")
            return []
    
    def download_image(self, url: str) -> Optional[Image.Image]:
        """Download an image from a URL."""
        try:
            response = requests.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return Image.open(BytesIO(response.content))
            else:
                logger.error(f"❌ Failed to download image: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to download image: {str(e)}")
            return None
    
    def classify_furniture(self, image_data: dict, label: dict) -> str:
        """Classify furniture type based on bounding box dimensions."""
        try:
            # Get image dimensions
            img_width = image_data.get("width", 1)
            img_height = image_data.get("height", 1)
            
            # Get bounding box dimensions (YOLO format: x, y, width, height - normalized)
            bbox = label.get("bbox", {})
            bbox_width = bbox.get("width", 0) * img_width
            bbox_height = bbox.get("height", 0) * img_height
            
            # Calculate aspect ratio and relative size
            aspect_ratio = bbox_width / bbox_height if bbox_height > 0 else 1
            rel_size = (bbox_width * bbox_height) / (img_width * img_height)
            
            # Get class ID
            class_id = label.get("class_id", 0)
            
            # Try to classify based on dimensions
            for min_ar, max_ar, min_size, max_size, ftype in FURNITURE_TYPES:
                if min_ar <= aspect_ratio <= max_ar and min_size <= rel_size <= max_size:
                    return ftype
            
            # Fallback to class ID mapping
            if class_id in DEFAULT_CLASS_MAPPINGS:
                return DEFAULT_CLASS_MAPPINGS[class_id]
            
            # Default fallback
            return "furniture"
        except Exception as e:
            logger.error(f"❌ Error classifying furniture: {str(e)}")
            return "furniture"
    
    def analyze_dataset(self, dataset_id: str, limit: int = 50) -> Dict[int, Dict[str, Any]]:
        """Analyze a dataset and create a custom class mapping."""
        # Get dataset details
        dataset = self.get_dataset_details(dataset_id)
        if not dataset:
            logger.error(f"❌ Dataset {dataset_id} not found")
            return {}
        
        dataset_name = dataset.get('name', 'Unknown')
        if not images:
            return {}
        
        # Initialize counters for each class ID
        class_counts = {}
        class_mappings = {}
        
        # Process each image
        for img_data in images:
            # Process each label
            for label in img_data.get('labels', []):
                class_id = label.get('class_id', 0)
                
                # Classify the furniture type
                furniture_type = self.classify_furniture(img_data, label)
                
                # Update counters
                if class_id not in class_counts:
                    class_counts[class_id] = {}
                
                if furniture_type not in class_counts[class_id]:
                    class_counts[class_id][furniture_type] = 0
                
                class_counts[class_id][furniture_type] += 1
        
        # Determine the most common furniture type for each class ID
        for class_id, counts in class_counts.items():
            if counts:
                # Get the most common furniture type
                most_common = max(counts.items(), key=lambda x: x[1])
                furniture_type = most_common[0]
                count = most_common[1]
                
                logger.info(f"Class {class_id}: {furniture_type} ({count} instances)")
                class_mappings[class_id] = furniture_type
                logger.info(f"Class {class_id}: {furniture_type} ({most_common[1]}/{stats['total']} = {class_mapping[class_id]['percentage']}%)")
        
        # Save mapping to config
        self.config["class_mappings"] = self.config.get("class_mappings", {})
        self.config["class_mappings"][dataset_id] = {str(k): v["name"] for k, v in class_mapping.items()}
        self.save_config()
        
        return class_mapping
    
    def update_enhanced_image_listing(self) -> bool:
        """Update the enhanced_image_listing.py script to use our custom class mappings."""
        try:
            logger.info("Updating enhanced_image_listing.py script...")
            
            script_path = Path("enhanced_image_listing.py")
            if not script_path.exists():
                logger.error(f"❌ Script not found: {script_path}")
                return False
            
            # Read the script content
            with open(script_path, 'r') as f:
                content = f.read()
            
            # Create a backup
            backup_path = script_path.with_suffix('.py.bak2')
            with open(backup_path, 'w') as f:
                f.write(content)
            logger.info(f"✅ Created backup at {backup_path}")
            
            # Modify the script to load and use custom class mappings
            updated_content = content
            
            # 1. Add import for json if not already present
            if "import json" not in content:
                import_pos = content.find("import")
                if import_pos >= 0:
                    updated_content = content[:import_pos] + "import json\n" + content[import_pos:]
            
            # 2. Add custom class mapping method
            custom_method = '''
    def get_custom_class_mappings(self, dataset_id: str) -> dict:
        """Get custom class mappings from furniture_config.json if available."""
        config_path = OUTPUT_DIR / "furniture_config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    
                mappings = config.get("class_mappings", {}).get(dataset_id)
                if mappings:
                    # Convert string keys to integers
                    return {int(k): v for k, v in mappings.items()}
            except Exception:
                pass
        return {}
'''
            
            # Find a good place to insert the custom method
            class_def_pos = updated_content.find("class EnhancedImageListing:")
            if class_def_pos >= 0:
                # Find the first method after class definition
                first_method_pos = updated_content.find("    def ", class_def_pos)
                if first_method_pos >= 0:
                    updated_content = updated_content[:first_method_pos] + custom_method + updated_content[first_method_pos:]
            
            # 3. Update the get_class_names method to use custom mappings
            class_map_code = '''
            # Try to get custom class mappings first
            custom_mappings = self.get_custom_class_mappings(dataset_id)
            
            # Create a mapping with default names
            class_map = {}
            common_classes = {
                0: "bed", 1: "chair", 2: "table", 3: "lamp", 4: "sofa",
                5: "desk", 6: "nightstand", 7: "tv", 8: "mirror", 9: "wardrobe"
            }
            
            # Use custom mappings if available
            if custom_mappings:
                logger.info(f"✅ Using custom class mappings for dataset {dataset_id}")
                common_classes.update(custom_mappings)
'''
            
            old_class_map_code = '''
            # Create a mapping with default names
            class_map = {}
            common_classes = {
                0: "bed", 1: "chair", 2: "table", 3: "lamp", 4: "sofa",
                5: "desk", 6: "nightstand", 7: "tv", 8: "mirror", 9: "wardrobe"
            }
'''
            
            updated_content = updated_content.replace(old_class_map_code, class_map_code)
            
            # 4. Add confidence threshold parameter to visualization method
            old_vis_def = "def visualize_image_with_labels(self, image_data: dict, class_map: dict, output_path: Path = None) -> Path:"
            new_vis_def = "def visualize_image_with_labels(self, image_data: dict, class_map: dict, output_path: Path = None, confidence_threshold: float = 0.5) -> Path:"
            updated_content = updated_content.replace(old_vis_def, new_vis_def)
            
            # 5. Add confidence threshold check in the label loop
            confidence_check = '''
                # Skip labels with low confidence
                confidence = label.get('confidence', 1.0)
                if confidence < confidence_threshold:
                    continue
'''
            
            yolo_format_line = "                # YOLO format: x, y, width, height (normalized)"
            updated_content = updated_content.replace(yolo_format_line, confidence_check + yolo_format_line)
            
            # Write the updated content
            with open(script_path, 'w') as f:
                f.write(updated_content)
            
            logger.info(f"✅ Updated {script_path} with custom class mapping support")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update enhanced_image_listing.py: {str(e)}")
            return False
    
    def load_config(self) -> Dict[str, Any]:
        """Load the configuration from file."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def save_config(self) -> None:
        """Save the configuration to file."""
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def process_dataset(self, dataset_id: str) -> bool:
        """Process a dataset to create custom furniture class mappings."""
        # Check server health
        if not self.check_server_health():
            return False
        
        # Analyze dataset and create class mapping
        class_mapping = self.analyze_dataset(dataset_id)
        if not class_mapping:
            return False
        
        # Update enhanced image listing script
        if not self.update_enhanced_image_listing():
            return False
        
        logger.info(f"✅ Successfully created custom furniture mappings for dataset {dataset_id}")
        logger.info("Class mappings:")
        for class_id, info in class_mapping.items():
            logger.info(f"  - Class {class_id}: {info['name']} ({info['percentage']}%)")
        
        return True

def main():
    """Main function to run the furniture classifier."""
    parser = argparse.ArgumentParser(description="Classify furniture in hotel images")
    parser.add_argument("--dataset", help="Dataset ID to analyze")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of images to analyze")
    parser.add_argument("--list", action="store_true", help="List available datasets")
    args = parser.parse_args()
    
    classifier = FurnitureClassifier()
    
    # Check server health
    if not classifier.check_server_health():
        logger.error("❌ Server is not healthy. Exiting.")
        return 1
    
    # List datasets if requested
    if args.list:
        datasets = classifier.get_datasets()
        if not datasets:
            logger.error("❌ No datasets found")
            return 1
        
        logger.info("\nAvailable datasets:")
        for i, dataset in enumerate(datasets, 1):
            if isinstance(dataset, dict):
                logger.info(f"{i}. {dataset.get('name')} (ID: {dataset.get('id')})")
            else:
                logger.info(f"{i}. {dataset}")
                
        # If datasets are just IDs, fetch details for each
        if datasets and isinstance(datasets[0], str):
            logger.info("\nFetching dataset details...")
            for i, dataset_id in enumerate(datasets, 1):
                details = classifier.get_dataset_details(dataset_id)
                if details:
                    logger.info(f"{i}. {details.get('name')} (ID: {dataset_id})")
                else:
                    logger.info(f"{i}. Unknown dataset (ID: {dataset_id})")
        
        return 0
    
    # Process dataset if ID provided
    if args.dataset:
        if not classifier.process_dataset(args.dataset):
            logger.error(f"❌ Failed to process dataset {args.dataset}")
            return 1
    else:
        logger.error("❌ No dataset ID provided. Use --dataset <id> or --list to see available datasets.")
        return 1
    
    logger.info("\n✅ Furniture classification completed successfully!")
    logger.info(f"   Run 'python enhanced_image_listing.py --dataset {args.dataset} --limit 20' to see the results")
    
    return 0

if __name__ == "__main__":
    exit(main())
