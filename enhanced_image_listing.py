#!/usr/bin/env python3
"""
Enhanced Image Listing with Labels

This script builds and renders an enhanced listing of images with their labels
from the dataset annotation service. It provides a visual representation of the
images and their associated labels, making it easier to verify the data.

FEATURES:
- Displays images with or without labels
- MongoDB integration for enhanced metadata storage
- Performance optimization for large datasets
- Dataset image management capabilities
- Label/Annotation display and statistics
"""

import os
import sys
import requests
import json
import time
from pathlib import Path
import tempfile
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
import argparse
import logging
from tabulate import tabulate
import pymongo
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('enhanced_listing.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
API_URL = "http://localhost:8000/api/v1"
DEFAULT_TIMEOUT = 15  # seconds
OUTPUT_DIR = Path("output")

# MongoDB Configuration
MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB = "ultralytics_annotation"
MONGO_COLLECTION_DATASETS = "datasets"
MONGO_COLLECTION_IMAGES = "images"
MONGO_COLLECTION_LABELS = "labels"

# Performance settings
MAX_WORKERS = 8  # Number of threads for parallel processing
BATCH_SIZE = 50  # Number of images to process in a batch

class EnhancedImageListing:
    """Enhanced image listing with labels visualization."""
    
    def __init__(self, api_url: str = API_URL, timeout: int = DEFAULT_TIMEOUT, use_mongodb: bool = True):
        """Initialize the enhanced image listing."""
        self.api_url = api_url
        self.timeout = timeout
        self.datasets = []
        self.use_mongodb = use_mongodb
        
        # Create output directory if it doesn't exist
        OUTPUT_DIR.mkdir(exist_ok=True)
        
        # Initialize MongoDB connection if enabled
        self.mongo_client = None
        self.mongo_db = None
        if self.use_mongodb:
            try:
                self.mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
                # Test connection
                self.mongo_client.server_info()
                self.mongo_db = self.mongo_client[MONGO_DB]
                logger.info("✅ Connected to MongoDB")
            except Exception as e:
                logger.warning(f"⚠️ MongoDB connection failed: {str(e)}. Continuing without MongoDB.")
                self.use_mongodb = False

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
    
    def check_server_health(self) -> bool:
        """Check if the server is up and running."""
        try:
            logger.info("Checking server health...")
            response = requests.get(f"{self.api_url}/health", timeout=self.timeout)
            if response.status_code == 200:
                logger.info("✅ Server is healthy")
                return True
            else:
                logger.error(f"❌ Server returned status code {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Server health check failed: {str(e)}")
            return False
    
    def get_datasets(self) -> list:
        """Get all datasets from the server."""
        try:
            logger.info("Retrieving datasets...")
            response = requests.get(f"{self.api_url}/datasets/", timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                self.datasets = data.get('datasets', [])
                logger.info(f"✅ Retrieved {len(self.datasets)} datasets")
                return self.datasets
            else:
                logger.error(f"❌ Failed to retrieve datasets: {response.status_code}")
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to retrieve datasets: {str(e)}")
            return []
    
    def get_dataset_details(self, dataset_id: str) -> dict:
        """Get details for a specific dataset."""
        try:
            logger.info(f"Retrieving details for dataset {dataset_id}...")
            response = requests.get(f"{self.api_url}/datasets/{dataset_id}", timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Retrieved details for dataset {dataset_id}")
                return data
            else:
                logger.error(f"❌ Failed to retrieve dataset details: {response.status_code}")
                return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to retrieve dataset details: {str(e)}")
            return {}
    
    def get_dataset_images(self, dataset_id: str, limit: int = 100, with_labels: bool = True) -> list:
        """Get images for a specific dataset."""
        try:
            # First check if we have this data in MongoDB
            if self.use_mongodb and self.mongo_db:
                images = list(self.mongo_db[MONGO_COLLECTION_IMAGES].find(
                    {"dataset_id": dataset_id},
                    {"_id": 0}
                ).limit(limit))
                
                if images:
                    logger.info(f"✅ Retrieved {len(images)} images from MongoDB for dataset {dataset_id}")
                    
                    # If we need labels, fetch them
                    if with_labels:
                        for image in images:
                            image_id = image.get('id')
                            if image_id:
                                labels = list(self.mongo_db[MONGO_COLLECTION_LABELS].find(
                                    {"image_id": image_id},
                                    {"_id": 0}
                                ))
                                image['labels'] = labels
                    
                    return images
            
            # If not in MongoDB or MongoDB is disabled, fetch from API
            logger.info(f"Retrieving images for dataset {dataset_id} from API...")
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
                
                # Store in MongoDB if enabled
                if self.use_mongodb and self.mongo_db:
                    self._store_images_in_mongodb(images, dataset_id)
                
                return images
            else:
                logger.error(f"❌ Failed to retrieve dataset images: {response.status_code}")
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to retrieve dataset images: {str(e)}")
            return []
    
    def download_image(self, image_url: str) -> Image.Image:
        """Download an image from a URL."""
        try:
            response = requests.get(image_url, timeout=self.timeout)
            if response.status_code == 200:
                img = Image.open(io.BytesIO(response.content))
                return img
            else:
                logger.error(f"❌ Failed to download image: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to download image: {str(e)}")
            return None
    
    def get_class_names(self, dataset_id: str, images: list = None) -> dict:
        """Get class names for a dataset by first trying the API endpoint and then extracting from labels."""
        try:
            # Try to get class definitions from API first
            logger.info(f"Retrieving class definitions for dataset {dataset_id}...")
            try:
                response = requests.get(f"{self.api_url}/datasets/{dataset_id}/classes", timeout=self.timeout)
                
                if response.status_code == 200:
                    classes = response.json().get('classes', [])
                    class_map = {cls.get('id'): cls.get('name', f"Class {cls.get('id')}") for cls in classes}
                    logger.info(f"✅ Retrieved {len(class_map)} class definitions from API")
                    return class_map
            except Exception:
                # Silently continue to fallback method
                pass
                
            # Fallback: Extract class IDs from the labels in the provided images
            logger.info("Extracting class definitions from labels...")
            
            # If images not provided, fetch them
            if not images:
                images = self.get_dataset_images(dataset_id, limit=50, with_labels=True)
            
            # Extract unique class IDs from labels
            class_ids = set()
            for image in images:
                for label in image.get('labels', []):
                    class_ids.add(label.get('class_id', 0))
            
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
            
            for class_id in class_ids:
                if class_id in common_classes:
                    class_map[class_id] = common_classes[class_id]
                else:
                    class_map[class_id] = f"Class {class_id}"
            
            logger.info(f"✅ Extracted {len(class_map)} class definitions from labels")
            return class_map
            
        except Exception as e:
            logger.error(f"❌ Failed to retrieve class definitions: {str(e)}")
            return {0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane"}
    
    def visualize_image_with_labels(self, image_data: dict, class_map: dict, output_path: Path = None, confidence_threshold: float = 0.5) -> Path:
        """Visualize an image with its labels."""
        try:
            # Download the image
            img_url = image_data.get('download_url')
            if not img_url:
                logger.error(f"❌ Image URL not found for {image_data.get('filename')}")
                return None
            
            img = self.download_image(img_url)
            if img is None:
                return None
            
            # Create figure and axis
            fig, ax = plt.subplots(1, figsize=(10, 10))
            
            # Display the image
            ax.imshow(np.array(img))
            
            # Get image dimensions
            img_width, img_height = img.size
            
            # Draw bounding boxes for labels
            labels = image_data.get('labels', [])
            for label in labels:
                # Skip labels with low confidence
                confidence = label.get('confidence', 1.0)
                if confidence < confidence_threshold:
                    continue
                # YOLO format: x, y, width, height (normalized)
                x = label.get('x_center', 0)
                y = label.get('y_center', 0)
                width = label.get('width', 0)
                height = label.get('height', 0)
                class_id = label.get('class_id', 0)
                class_name = class_map.get(class_id, f"Class {class_id}")
                
                # Convert normalized coordinates to pixel coordinates
                x_px = x * img_width
                y_px = y * img_height
                width_px = width * img_width
                height_px = height * img_height
                
                # Calculate top-left corner for rectangle (matplotlib uses top-left)
                rect_x = x_px - (width_px / 2)
                rect_y = y_px - (height_px / 2)
                
                # Add rectangle and label
                rect = Rectangle(
                    (rect_x, rect_y), width_px, height_px, 
                    linewidth=2, edgecolor='r', facecolor='none'
                )
                ax.add_patch(rect)
                ax.text(
                    rect_x, rect_y - 5, class_name, 
                    color='white', fontsize=12, 
                    bbox=dict(facecolor='red', alpha=0.7)
                )
            
            # Remove axes
            ax.axis('off')
            
            # Save or return the figure
            if output_path:
                plt.savefig(output_path, bbox_inches='tight', pad_inches=0.1)
                plt.close(fig)
                return output_path
            else:
                # Save to temporary file
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                    plt.savefig(tmp_file.name, bbox_inches='tight', pad_inches=0.1)
                    plt.close(fig)
                    return Path(tmp_file.name)
                
        except Exception as e:
            logger.error(f"❌ Failed to visualize image: {str(e)}")
            return None
    
    def create_html_gallery(self, dataset_id: str, images: list, output_path: Path, confidence_threshold: float = 0.5) -> Path:
        """Create an HTML gallery of images with labels."""
        try:
            dataset = self.get_dataset_details(dataset_id)
            dataset_name = dataset.get('name', 'Unknown Dataset')
            
            # Get class definitions using the provided images
            class_map = self.get_class_names(dataset_id, images)
            
            # Calculate statistics
            total_images = len(images)
            images_with_labels = sum(1 for img in images if img.get('labels', []))
            images_without_labels = total_images - images_with_labels
            
            # Start HTML content
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Enhanced Image Listing - {dataset_name}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #333; }}
                    .gallery {{ 
                        display: grid; 
                        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                        gap: 20px; 
                    }}
                    .image-card {{ 
                        border: 1px solid #ddd; 
                        border-radius: 8px;
                        overflow: hidden;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    }}
                    .image-container {{ position: relative; }}
                    .image-container img {{ width: 100%; height: auto; }}
                    .image-info {{ padding: 10px; }}
                    .label-count {{ 
                        position: absolute; 
                        top: 10px; 
                        right: 10px; 
                        padding: 5px 10px; 
                        border-radius: 15px; 
                        color: white;
                    }}
                    .has-labels {{ background: rgba(255,0,0,0.7); }}
                    .no-labels {{ background: rgba(0,0,255,0.7); }}
                    .label-list {{ 
                        margin-top: 10px; 
                        background: #f8f8f8; 
                        padding: 10px; 
                        border-radius: 5px; 
                    }}
                    .label-item {{ margin-bottom: 5px; }}
                    .stats {{ 
                        background: #f0f0f0; 
                        padding: 15px; 
                        border-radius: 8px; 
                        margin-bottom: 20px; 
                    }}
                    .stats-grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                        gap: 10px;
                    }}
                    .stat-card {{
                        background: white;
                        padding: 10px;
                        border-radius: 5px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        text-align: center;
                    }}
                    .stat-value {{
                        font-size: 24px;
                        font-weight: bold;
                        margin: 10px 0;
                    }}
                    .filter-controls {{
                        margin-bottom: 20px;
                        padding: 15px;
                        background: #f0f0f0;
                        border-radius: 8px;
                    }}
                    .filter-btn {{
                        padding: 8px 16px;
                        margin-right: 10px;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                    }}
                    .filter-btn.active {{
                        background: #007bff;
                        color: white;
                    }}
                    .annotation-ready {{
                        background: #e3f2fd;
                        border-left: 4px solid #2196f3;
                        padding: 10px;
                        margin-top: 10px;
                    }}
                </style>
                <script>
                    function filterImages(filter) {{
                        const cards = document.querySelectorAll('.image-card');
                        cards.forEach(card => {{
                            const hasLabels = card.getAttribute('data-has-labels') === 'true';
                            
                            if (filter === 'all' || 
                                (filter === 'with-labels' && hasLabels) || 
                                (filter === 'without-labels' && !hasLabels)) {{
                                card.style.display = 'block';
                            }} else {{
                                card.style.display = 'none';
                            }}
                        }});
                        
                        // Update active button
                        document.querySelectorAll('.filter-btn').forEach(btn => {{
                            btn.classList.remove('active');
                        }});
                        document.getElementById('btn-' + filter).classList.add('active');
                    }}
                </script>
            </head>
            <body>
                <h1>Enhanced Image Listing - {dataset_name}</h1>
                
                <div class="stats">
                    <h2>Dataset Statistics</h2>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div>Total Images</div>
                            <div class="stat-value">{total_images}</div>
                        </div>
                        <div class="stat-card">
                            <div>Images with Labels</div>
                            <div class="stat-value">{images_with_labels}</div>
                        </div>
                        <div class="stat-card">
                            <div>Images without Labels</div>
                            <div class="stat-value">{images_without_labels}</div>
                        </div>
                        <div class="stat-card">
                            <div>Status</div>
                            <div class="stat-value">{dataset.get('status', 'Unknown')}</div>
                        </div>
                    </div>
                    <p><strong>Created:</strong> {dataset.get('created_at', 'Unknown')}</p>
                </div>
                
                <div class="filter-controls">
                    <h3>Filter Images</h3>
                    <button id="btn-all" class="filter-btn active" onclick="filterImages('all')">All Images</button>
                    <button id="btn-with-labels" class="filter-btn" onclick="filterImages('with-labels')">With Labels</button>
                    <button id="btn-without-labels" class="filter-btn" onclick="filterImages('without-labels')">Without Labels</button>
                </div>
                
                <div class="gallery">
            """
            
            # Create a directory for visualizations if it doesn't exist
            vis_dir = OUTPUT_DIR / dataset_id
            vis_dir.mkdir(exist_ok=True)
            
            # Process images in parallel for better performance
            def process_image(image):
                image_id = image.get('id', 'unknown')
                filename = image.get('filename', 'Unknown')
                labels = image.get('labels', [])
                has_labels = len(labels) > 0
                
                # Visualize image with labels
                vis_path = vis_dir / f"{image_id}.png"
                self.visualize_image_with_labels(image, class_map, vis_path)
                
                # Create HTML for this image
                html = f"""
                <div class="image-card" data-has-labels="{str(has_labels).lower()}">
                    <div class="image-container">
                        <img src="{vis_path.relative_to(OUTPUT_DIR)}" alt="{filename}">
                        <div class="label-count {'has-labels' if has_labels else 'no-labels'}">
                            {len(labels) if has_labels else 'No'} labels
                        </div>
                    </div>
                    <div class="image-info">
                        <h3>{filename}</h3>
                        <p>ID: {image_id}</p>
                        <p>Dimensions: {image.get('width', 0)}x{image.get('height', 0)}</p>
                """
                
                if has_labels:
                    html += f"""
                        <div class="label-list">
                            <h4>Labels:</h4>
                    """
                    
                    for label in labels:
                        class_id = label.get('class_id', 0)
                        class_name = class_map.get(class_id, f"Class {class_id}")
                        x = label.get('x_center', 0)
                        y = label.get('y_center', 0)
                        width = label.get('width', 0)
                        height = label.get('height', 0)
                        
                        html += f"""
                            <div class="label-item">
                                <strong>{class_name}</strong> at ({x:.3f}, {y:.3f}) with size {width:.3f}x{height:.3f}
                            </div>
                        """
                    
                    html += """
                        </div>
                    """
                else:
                    html += """
                        <div class="annotation-ready">
                            <p>This image is ready for annotation.</p>
                        </div>
                    """
                
                html += """
                    </div>
                </div>
                """
                return html
            
            # Process images in parallel
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                image_htmls = list(tqdm(
                    executor.map(process_image, images),
                    total=len(images),
                    desc="Processing images"
                ))
            
            # Add all image HTML to the gallery
            html_content += '\n'.join(image_htmls)
            
            # Close HTML content
            html_content += """
                </div>
            </body>
            </html>
            """
            
            # Write HTML to file
            with open(output_path, 'w') as f:
                f.write(html_content)
            
            logger.info(f"✅ Created HTML gallery at {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Failed to create HTML gallery: {str(e)}")
            return None
    
    def process_dataset(self, dataset_id: str, limit: int = 20, confidence_threshold: float = 0.5) -> Path:
        """Process a dataset and create an enhanced image listing."""
        # Get dataset details
        dataset = self.get_dataset_details(dataset_id)
        if not dataset:
            logger.error(f"❌ Dataset {dataset_id} not found")
            return None
        
        dataset_name = dataset.get('name', 'Unknown')
        logger.info(f"Processing dataset: {dataset_name} with confidence threshold: {confidence_threshold}")
        
        # Get images with labels
        images = self.get_dataset_images(dataset_id, limit=limit, with_labels=True)
        if not images:
            logger.error(f"❌ No images found for dataset {dataset_id}")
            return None
            
        # Get class definitions using the fetched images
        class_map = self.get_class_names(dataset_id, images)
        
        # Create HTML gallery with confidence threshold
        output_path = OUTPUT_DIR / f"{dataset_id}_gallery_conf{confidence_threshold}.html"
        html_path = self.create_html_gallery(dataset_id, images, output_path, confidence_threshold)
        
        return html_path
    
    def list_datasets_with_stats(self) -> None:
        """List all datasets with statistics."""
        datasets = self.get_datasets()
        if not datasets:
            print("No datasets found.")
            return
        
        table_data = []
        for ds in datasets:
            ds_id = ds.get('id', 'unknown')
            name = ds.get('name', 'Unknown')
            status = ds.get('status', 'Unknown')
            images = ds.get('image_count', 0)
            created = ds.get('created_at', 'Unknown')[:16].replace('T', ' ')
            
            table_data.append([ds_id, name, status, images, created])
        
        headers = ["ID", "Name", "Status", "Images", "Created"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    def run_pipeline(self, dataset_id: str = None, limit: int = 20, confidence_threshold: float = 0.5) -> None:
        """Run the enhanced image listing pipeline."""
        # Check server health
        if not self.check_server_health():
            logger.error("❌ Server is not healthy. Exiting...")
            return
        
        # If no dataset ID provided, list available datasets
        if not dataset_id:
            self.list_datasets_with_stats()
            return
        
        # Process the specified dataset
        html_path = self.process_dataset(dataset_id, limit, confidence_threshold)
        if html_path:
            print(f"\n✅ Enhanced image listing created successfully!")
            print(f"   View the gallery at: {html_path}")
            
            # Try to open the HTML file in the default browser
            try:
                import webbrowser
                webbrowser.open(f"file://{html_path.absolute()}")
                print("   Opening gallery in your default web browser...")
            except:
                pass

def main():
    """Main function to run the enhanced image listing pipeline."""
    parser = argparse.ArgumentParser(description="Enhanced Image Listing with Labels")
    parser.add_argument("--url", default=API_URL, help="API URL (default: http://localhost:8000/api/v1)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Request timeout in seconds")
    parser.add_argument("--dataset", help="Dataset ID to process")
    parser.add_argument("--limit", type=int, default=20, help="Limit for image listing")
    parser.add_argument("--confidence", type=float, default=0.5, help="Confidence threshold for labels (0.0-1.0)")
    
    args = parser.parse_args()
    
    pipeline = EnhancedImageListing(api_url=args.url, timeout=args.timeout)
    pipeline.run_pipeline(args.dataset, args.limit, confidence_threshold=args.confidence)

if __name__ == "__main__":
    main()
