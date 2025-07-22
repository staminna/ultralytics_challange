#!/usr/bin/env python3
"""
Furniture Classifier for YOLO Dataset
Analyzes hotel images and bounding boxes to classify furniture types based on dimensions
"""

import json
import argparse
import requests
import logging
from pathlib import Path
from PIL import Image
from io import BytesIO
from typing import Dict, List, Any, Optional

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

# Furniture classification rules based on aspect ratio and size
FURNITURE_RULES = [
    # (min_aspect_ratio, max_aspect_ratio, min_rel_size, max_rel_size, furniture_type)
    (0.8, 1.5, 0.05, 0.15, "chair"),      # Square-ish, small
    (1.5, 3.0, 0.05, 0.2, "bench"),       # Wide, small
    (0.8, 1.5, 0.15, 0.3, "table"),       # Square-ish, medium
    (1.5, 3.0, 0.15, 0.4, "sofa"),        # Wide, medium
    (0.5, 0.8, 0.1, 0.3, "cabinet"),      # Tall, medium
    (0.8, 2.0, 0.3, 1.0, "bed"),          # Large furniture
]

# Default class mappings
DEFAULT_MAPPINGS = {0: "bed", 1: "chair", 2: "table"}

class FurnitureClassifier:
    def __init__(self):
        self.api_url = API_BASE_URL
        self.timeout = TIMEOUT
        self.config = self._load_config()
    
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
    
    def get_dataset_details(self, dataset_id: str) -> Optional[Dict]:
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
    
    def get_dataset_images(self, dataset_id: str, limit: int = 50) -> List[Dict]:
        """Get images with labels for a dataset."""
        try:
            logger.info(f"Retrieving images for dataset {dataset_id}...")
            params = {"limit": limit, "with_labels": "true"}
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
    
    def classify_furniture(self, image_data: Dict, label: Dict) -> str:
        """Classify furniture type based on bounding box dimensions."""
        try:
            # Get image dimensions
            img_width = image_data.get("width", 1)
            img_height = image_data.get("height", 1)
            
            # Get bounding box dimensions
            bbox = label.get("bbox", {})
            bbox_width = bbox.get("width", 0) * img_width
            bbox_height = bbox.get("height", 0) * img_height
            
            # Calculate aspect ratio and relative size
            aspect_ratio = bbox_width / bbox_height if bbox_height > 0 else 1
            rel_size = (bbox_width * bbox_height) / (img_width * img_height)
            
            # Get class ID
            class_id = label.get("class_id", 0)
            
            # Try to classify based on dimensions
            for min_ar, max_ar, min_size, max_size, ftype in FURNITURE_RULES:
                if min_ar <= aspect_ratio <= max_ar and min_size <= rel_size <= max_size:
                    return ftype
            
            # Fallback to class ID mapping
            return DEFAULT_MAPPINGS.get(class_id, "furniture")
        except Exception as e:
            logger.error(f"❌ Error classifying furniture: {str(e)}")
            return "furniture"
    
    def analyze_dataset(self, dataset_id: str, limit: int = 50) -> Dict[int, str]:
        """Analyze a dataset and create a custom class mapping."""
        # Get dataset details
        dataset = self.get_dataset_details(dataset_id)
        if not dataset:
            logger.error(f"❌ Dataset {dataset_id} not found")
            return {}
        
        dataset_name = dataset.get('name', 'Unknown')
        logger.info(f"Analyzing dataset: {dataset_name}")
        
        # Get images with labels
        images = self.get_dataset_images(dataset_id, limit)
        if not images:
            logger.error(f"❌ No images found for dataset {dataset_id}")
            return {}
        
        # Initialize class statistics
        class_stats = {}
        
        # Process each image
        for image_data in images:
            # Process labels
            for label in image_data.get('labels', []):
                class_id = label.get('class_id', 0)
                
                # Classify furniture type
                furniture_type = self.classify_furniture(image_data, label)
                
                # Update statistics
                if class_id not in class_stats:
                    class_stats[class_id] = {}
                
                if furniture_type not in class_stats[class_id]:
                    class_stats[class_id][furniture_type] = 0
                
                class_stats[class_id][furniture_type] += 1
        
        # Create final class mapping based on most common furniture type
        class_mapping = {}
        for class_id, types in class_stats.items():
            if types:
                # Find most common furniture type
                most_common = max(types.items(), key=lambda x: x[1])
                furniture_type = most_common[0]
                count = most_common[1]
                
                class_mapping[class_id] = furniture_type
                logger.info(f"Class {class_id}: {furniture_type} ({count} instances)")
        
        # Save mapping to config
        self._save_class_mapping(dataset_id, class_mapping)
        
        return class_mapping
    
    def _load_config(self) -> Dict:
        """Load configuration from file."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_config(self) -> None:
        """Save configuration to file."""
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def _save_class_mapping(self, dataset_id: str, class_mapping: Dict[int, str]) -> None:
        """Save class mapping to config file."""
        # Initialize class_mappings if not exists
        if "class_mappings" not in self.config:
            self.config["class_mappings"] = {}
        
        # Save mapping for this dataset
        self.config["class_mappings"][dataset_id] = {str(k): v for k, v in class_mapping.items()}
        self._save_config()
        
        logger.info(f"✅ Saved custom class mappings for dataset {dataset_id}")
    
    def update_enhanced_image_listing(self) -> bool:
        """Update the enhanced_image_listing.py script to use custom class mappings."""
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
            backup_path = script_path.with_suffix('.py.bak')
            with open(backup_path, 'w') as f:
                f.write(content)
            logger.info(f"✅ Created backup at {backup_path}")
            
            # Add import for json if not already present
            if "import json" not in content:
                import_pos = content.find("import")
                if import_pos >= 0:
                    content = content[:import_pos] + "import json\n" + content[import_pos:]
            
            # Add custom class mapping method
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
            
            # Find a good insertion point for the custom method
            class_def_pos = content.find("class EnhancedImageListing:")
            if class_def_pos >= 0:
                # Find the first method after class definition
                first_method_pos = content.find("    def ", class_def_pos)
                if first_method_pos >= 0:
                    content = content[:first_method_pos] + custom_method + content[first_method_pos:]
            
            # Update the get_class_names method to use custom mappings
            old_class_map_code = '''
            # Create a mapping with default names
            class_map = {}
            common_classes = {
                0: "bed", 1: "chair", 2: "table", 3: "lamp", 4: "sofa",
                5: "desk", 6: "nightstand", 7: "tv", 8: "mirror", 9: "wardrobe"
            }
'''
            
            new_class_map_code = '''
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
            
            content = content.replace(old_class_map_code, new_class_map_code)
            
            # Write the updated content
            with open(script_path, 'w') as f:
                f.write(content)
            
            logger.info(f"✅ Updated {script_path} with custom class mapping support")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update enhanced_image_listing.py: {str(e)}")
            return False
    
    def process_dataset(self, dataset_id: str, limit: int = 50) -> bool:
        """Process a dataset to create custom furniture class mappings."""
        # Check server health
        if not self.check_server_health():
            return False
        
        # Analyze dataset and create class mapping
        class_mapping = self.analyze_dataset(dataset_id, limit)
        if not class_mapping:
            logger.error(f"❌ Failed to process dataset {dataset_id}")
            return False
        
        # Update enhanced image listing script
        if not self.update_enhanced_image_listing():
            return False
        
        logger.info(f"✅ Successfully created custom furniture mappings for dataset {dataset_id}")
        return True

def main():
    """Main function to run the furniture classifier."""
    parser = argparse.ArgumentParser(description="Classify furniture in hotel images")
    parser.add_argument("--dataset", required=True, help="Dataset ID to analyze")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of images to analyze")
    args = parser.parse_args()
    
    classifier = FurnitureClassifier()
    success = classifier.process_dataset(args.dataset, args.limit)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
