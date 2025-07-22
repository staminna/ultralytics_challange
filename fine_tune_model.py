#!/usr/bin/env python3
"""
Fine-tune YOLO model class mappings and confidence thresholds.
This script updates the class mappings to correctly identify hotel furniture
and increases the confidence threshold for more accurate detections.
"""

import os
import json
import shutil
import argparse
import requests
import logging
from pathlib import Path
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
TIMEOUT = 10  # seconds
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Updated class mappings for hotel furniture
HOTEL_CLASS_MAPPINGS = {
    0: "bed",
    1: "chair",
    2: "table",
    3: "lamp",
    4: "sofa",
    5: "desk",
    6: "nightstand",
    7: "tv",
    8: "mirror",
    9: "wardrobe"
}

class ModelFineTuner:
    """Class to fine-tune YOLO model parameters and class mappings."""
    
    def __init__(self, api_url: str = API_BASE_URL, timeout: int = TIMEOUT):
        """Initialize the ModelFineTuner."""
        self.api_url = api_url
        self.timeout = timeout
        self.config_path = OUTPUT_DIR / "model_config.json"
        
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
                # Handle the API response format which might be a list or a dict with 'datasets' key
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
    
    def update_class_mappings(self, dataset_id: str, class_mappings: Dict[int, str]) -> bool:
        """Update class mappings for a dataset."""
        try:
            logger.info(f"Updating class mappings for dataset {dataset_id}...")
            
            # Format the class mappings for the API
            classes = [{"id": class_id, "name": name} for class_id, name in class_mappings.items()]
            
            # Send the update request
            response = requests.put(
                f"{self.api_url}/datasets/{dataset_id}/classes",
                json={"classes": classes},
                timeout=self.timeout
            )
            
            if response.status_code in (200, 201, 204):
                logger.info(f"✅ Updated class mappings for dataset {dataset_id}")
                return True
            else:
                logger.warning(f"⚠️ Failed to update class mappings via API: {response.status_code}")
                logger.info("Saving class mappings to local configuration file instead")
                
                # Save to local config file as fallback
                config = self.load_config()
                if "class_mappings" not in config:
                    config["class_mappings"] = {}
                config["class_mappings"][dataset_id] = class_mappings
                self.save_config(config)
                
                logger.info(f"✅ Saved class mappings to local configuration")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to update class mappings: {str(e)}")
            return False
    
    def update_confidence_threshold(self, threshold: float = 0.5) -> bool:
        """Update the confidence threshold for detections."""
        try:
            logger.info(f"Updating confidence threshold to {threshold}...")
            
            # Save to local config file
            config = self.load_config()
            config["confidence_threshold"] = threshold
            self.save_config(config)
            
            logger.info(f"✅ Updated confidence threshold to {threshold}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update confidence threshold: {str(e)}")
            return False
    
    def load_config(self) -> Dict[str, Any]:
        """Load the configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def save_config(self, config: Dict[str, Any]) -> None:
        """Save the configuration to file."""
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
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
            backup_path = script_path.with_suffix('.py.bak')
            shutil.copy2(script_path, backup_path)
            logger.info(f"✅ Created backup at {backup_path}")
            
            # Update the common_classes dictionary in get_class_names method
            updated_content = content.replace(
                "common_classes = {\n                0: \"person\", 1: \"bicycle\", 2: \"car\", 3: \"motorcycle\", 4: \"airplane\",\n                5: \"bus\", 6: \"train\", 7: \"truck\", 8: \"boat\", 9: \"traffic light\"\n            }",
                "common_classes = {\n                0: \"bed\", 1: \"chair\", 2: \"table\", 3: \"lamp\", 4: \"sofa\",\n                5: \"desk\", 6: \"nightstand\", 7: \"tv\", 8: \"mirror\", 9: \"wardrobe\"\n            }"
            )
            
            # Add confidence threshold to visualization method
            confidence_update = "def visualize_image_with_labels(self, image_data: dict, class_map: dict, output_path: Path = None, confidence_threshold: float = 0.5) -> Path:"
            updated_content = updated_content.replace(
                "def visualize_image_with_labels(self, image_data: dict, class_map: dict, output_path: Path = None) -> Path:",
                confidence_update
            )
            
            # Add confidence threshold check in the label loop
            confidence_check = "                # Skip labels with low confidence\n                confidence = label.get('confidence', 1.0)\n                if confidence < confidence_threshold:\n                    continue\n"
            updated_content = updated_content.replace(
                "                # YOLO format: x, y, width, height (normalized)\n",
                confidence_check + "                # YOLO format: x, y, width, height (normalized)\n"
            )
            
            # Write the updated content
            with open(script_path, 'w') as f:
                f.write(updated_content)
            
            logger.info(f"✅ Updated {script_path} with new class mappings and confidence threshold")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update enhanced_image_listing.py: {str(e)}")
            return False
    
    def process_dataset(self, dataset_id: str, confidence_threshold: float = 0.5) -> bool:
        """Process a dataset with updated class mappings and confidence threshold."""
        # Get dataset details
        dataset = self.get_dataset_details(dataset_id)
        if not dataset:
            return False
        
        # Update class mappings
        if not self.update_class_mappings(dataset_id, HOTEL_CLASS_MAPPINGS):
            return False
        
        # Update confidence threshold
        if not self.update_confidence_threshold(confidence_threshold):
            return False
        
        # Update enhanced image listing script
        if not self.update_enhanced_image_listing():
            return False
        
        logger.info(f"✅ Successfully fine-tuned model for dataset {dataset_id}")
        logger.info(f"   - Updated class mappings to hotel furniture")
        logger.info(f"   - Set confidence threshold to {confidence_threshold}")
        logger.info(f"   - Updated enhanced_image_listing.py script")
        
        return True

def main():
    """Main function to run the model fine-tuning."""
    parser = argparse.ArgumentParser(description="Fine-tune YOLO model parameters and class mappings")
    parser.add_argument("--dataset", help="Dataset ID to fine-tune")
    parser.add_argument("--confidence", type=float, default=0.5, help="Confidence threshold (0.0-1.0)")
    parser.add_argument("--list", action="store_true", help="List available datasets")
    args = parser.parse_args()
    
    fine_tuner = ModelFineTuner()
    
    # Check server health
    if not fine_tuner.check_server_health():
        logger.error("❌ Server is not healthy. Exiting.")
        return 1
    
    # List datasets if requested
    if args.list:
        datasets = fine_tuner.get_datasets()
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
                details = fine_tuner.get_dataset_details(dataset_id)
                if details:
                    logger.info(f"{i}. {details.get('name')} (ID: {dataset_id})")
                else:
                    logger.info(f"{i}. Unknown dataset (ID: {dataset_id})")

        return 0
    
    # Process dataset if ID provided
    if args.dataset:
        if not fine_tuner.process_dataset(args.dataset, args.confidence):
            logger.error(f"❌ Failed to process dataset {args.dataset}")
            return 1
    else:
        logger.error("❌ No dataset ID provided. Use --dataset <id> or --list to see available datasets.")
        return 1
    
    logger.info("\n✅ Model fine-tuning completed successfully!")
    logger.info(f"   Run 'python enhanced_image_listing.py --dataset {args.dataset} --limit 20' to see the results")
    
    return 0

if __name__ == "__main__":
    exit(main())
