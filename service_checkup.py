#!/usr/bin/env python3
"""
Service Checkup Script for YOLO Dataset Management System

This script performs comprehensive checks on the backend server, API endpoints,
and dataset management functionality. It provides detailed reports on:
- Server health and responsiveness
- Dataset listing with image counts
- Enhanced image listing with labels
- Dataset import status
"""

import os
import sys
import requests
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from tabulate import tabulate
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('service_checkup.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
API_URL = "http://localhost:8000/api/v1"
DEFAULT_TIMEOUT = 10  # seconds

class ServiceCheckup:
    """Service checkup for the YOLO dataset management system."""
    
    def __init__(self, api_url: str = API_URL, timeout: int = DEFAULT_TIMEOUT):
        """Initialize the service checkup."""
        self.api_url = api_url
        self.timeout = timeout
        self.health_status = False
        self.datasets = []
        self.start_time = datetime.now()
    
    def check_server_health(self) -> bool:
        """Check if the server is up and running."""
        try:
            logger.info("Checking server health...")
            response = requests.get(f"{self.api_url}/health", timeout=self.timeout)
            if response.status_code == 200:
                self.health_status = True
                logger.info("✅ Server is healthy")
                return True
            else:
                logger.error(f"❌ Server returned status code {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Server health check failed: {str(e)}")
            return False
    
    def get_datasets(self) -> List[Dict[str, Any]]:
        """Get all datasets from the server."""
        if not self.health_status:
            logger.warning("Server health check failed, skipping dataset retrieval")
            return []
        
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
    
    def get_dataset_details(self, dataset_id: str) -> Dict[str, Any]:
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
    
    def get_dataset_images(self, dataset_id: str, limit: int = 100, with_labels: bool = True) -> List[Dict[str, Any]]:
        """Get images for a specific dataset."""
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
                logger.error(f"❌ Failed to retrieve dataset images: {response.status_code}")
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to retrieve dataset images: {str(e)}")
            return []
    
    def get_image_details(self, dataset_id: str, image_id: str) -> Dict[str, Any]:
        """Get details for a specific image, including labels."""
        try:
            logger.info(f"Retrieving details for image {image_id}...")
            response = requests.get(
                f"{self.api_url}/datasets/{dataset_id}/images/{image_id}", 
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Retrieved details for image {image_id}")
                return data
            else:
                logger.error(f"❌ Failed to retrieve image details: {response.status_code}")
                return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to retrieve image details: {str(e)}")
            return {}
    
    def check_import_status(self, dataset_id: str) -> Dict[str, Any]:
        """Check the import status of a dataset."""
        try:
            logger.info(f"Checking import status for dataset {dataset_id}...")
            response = requests.get(
                f"{self.api_url}/datasets/{dataset_id}/import/status", 
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Retrieved import status for dataset {dataset_id}: {data.get('status')}")
                return data
            else:
                logger.error(f"❌ Failed to retrieve import status: {response.status_code}")
                return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to retrieve import status: {str(e)}")
            return {}
    
    def generate_dataset_report(self, dataset_id: Optional[str] = None) -> str:
        """Generate a report for datasets."""
        if not self.datasets and not dataset_id:
            self.get_datasets()
        
        if dataset_id:
            # Generate detailed report for a specific dataset
            dataset = self.get_dataset_details(dataset_id)
            if not dataset:
                return "Dataset not found or error retrieving dataset details."
            
            images = self.get_dataset_images(dataset_id)
            import_status = self.check_import_status(dataset_id)
            
            # Count images with and without labels
            images_with_labels = [img for img in images if img.get('labels', [])]
            
            report = [
                f"Dataset Report: {dataset.get('name', 'Unknown')}",
                f"ID: {dataset_id}",
                f"Description: {dataset.get('description', 'No description')}",
                f"Status: {dataset.get('status', 'Unknown')}",
                f"Created: {dataset.get('created_at', 'Unknown')}",
                f"Images: {dataset.get('image_count', 0)}",
                f"Images with labels: {len(images_with_labels)}/{len(images)}",
                f"Import status: {import_status.get('status', 'Unknown')}",
                f"Import progress: {import_status.get('progress', 0)}%"
            ]
            
            # Add sample images
            if images:
                report.append("\nSample Images:")
                for i, img in enumerate(images[:5]):
                    filename = img.get('filename', 'unknown')
                    img_id = img.get('id', 'unknown')
                    label_count = len(img.get('labels', []))
                    report.append(f"  {i+1}. {filename} (ID: {img_id}) - {label_count} labels")
            
            return "\n".join(report)
        else:
            # Generate summary report for all datasets
            if not self.datasets:
                return "No datasets found or error retrieving datasets."
            
            table_data = []
            for ds in self.datasets:
                ds_id = ds.get('id', 'unknown')
                name = ds.get('name', 'Unknown')
                status = ds.get('status', 'Unknown')
                images = ds.get('image_count', 0)
                created = ds.get('created_at', 'Unknown')[:16].replace('T', ' ')
                
                table_data.append([ds_id, name, status, images, created])
            
            headers = ["ID", "Name", "Status", "Images", "Created"]
            return tabulate(table_data, headers=headers, tablefmt="grid")
    
    def generate_image_report(self, dataset_id: str, limit: int = 10) -> str:
        """Generate a report for images in a dataset."""
        images = self.get_dataset_images(dataset_id, limit=limit)
        if not images:
            return f"No images found in dataset {dataset_id} or error retrieving images."
        
        table_data = []
        for img in images:
            img_id = img.get('id', 'unknown')
            filename = img.get('filename', 'Unknown')
            width = img.get('width', 0)
            height = img.get('height', 0)
            label_count = len(img.get('labels', []))
            
            table_data.append([img_id, filename, f"{width}x{height}", label_count])
        
        headers = ["ID", "Filename", "Dimensions", "Labels"]
        return tabulate(table_data, headers=headers, tablefmt="grid")
    
    def generate_label_report(self, dataset_id: str, image_id: str) -> str:
        """Generate a report for labels in an image."""
        image = self.get_image_details(dataset_id, image_id)
        if not image:
            return f"Image {image_id} not found in dataset {dataset_id} or error retrieving image."
        
        labels = image.get('labels', [])
        if not labels:
            return f"No labels found for image {image_id}."
        
        table_data = []
        for label in labels:
            label_id = label.get('id', 'unknown')
            class_id = label.get('class_id', 'unknown')
            class_name = label.get('class_name', 'Unknown')
            x = label.get('x', 0)
            y = label.get('y', 0)
            width = label.get('width', 0)
            height = label.get('height', 0)
            
            table_data.append([label_id, class_id, class_name, f"{x:.3f}", f"{y:.3f}", f"{width:.3f}", f"{height:.3f}"])
        
        headers = ["ID", "Class ID", "Class Name", "X", "Y", "Width", "Height"]
        return tabulate(table_data, headers=headers, tablefmt="grid")
    
    def run_full_checkup(self) -> Dict[str, Any]:
        """Run a full checkup of the service."""
        result = {
            "server_health": False,
            "datasets_count": 0,
            "datasets": [],
            "execution_time": 0
        }
        
        # Check server health
        result["server_health"] = self.check_server_health()
        if not result["server_health"]:
            result["execution_time"] = (datetime.now() - self.start_time).total_seconds()
            return result
        
        # Get datasets
        datasets = self.get_datasets()
        result["datasets_count"] = len(datasets)
        
        # Get details for each dataset
        for ds in datasets:
            ds_id = ds.get('id')
            if not ds_id:
                continue
                
            ds_details = self.get_dataset_details(ds_id)
            
            # Get sample images
            images = self.get_dataset_images(ds_id, limit=5)
            images_with_labels = [img for img in images if img.get('labels', [])]
            
            # Get import status
            import_status = self.check_import_status(ds_id)
            
            dataset_info = {
                "id": ds_id,
                "name": ds.get('name', 'Unknown'),
                "status": ds.get('status', 'Unknown'),
                "image_count": ds.get('image_count', 0),
                "images_with_labels": len(images_with_labels),
                "import_status": import_status.get('status', 'Unknown'),
                "import_progress": import_status.get('progress', 0)
            }
            
            result["datasets"].append(dataset_info)
        
        result["execution_time"] = (datetime.now() - self.start_time).total_seconds()
        return result
    
    def print_full_report(self) -> None:
        """Print a full report of the service checkup."""
        result = self.run_full_checkup()
        
        print("\n" + "="*60)
        print("🔍 SERVICE CHECKUP REPORT")
        print("="*60)
        
        # Server health
        health_icon = "✅" if result["server_health"] else "❌"
        print(f"\n{health_icon} Server Health: {'Healthy' if result['server_health'] else 'Unhealthy'}")
        
        if not result["server_health"]:
            print("\n❌ Server is not responding. Please check if the server is running.")
            return
        
        # Datasets summary
        print(f"\n📊 Datasets: {result['datasets_count']} total")
        
        if result["datasets"]:
            print("\nDataset Summary:")
            table_data = []
            for ds in result["datasets"]:
                status_icon = "✅" if ds["status"] == "ready" else "⏳"
                table_data.append([
                    status_icon,
                    ds["name"],
                    ds["image_count"],
                    f"{ds['images_with_labels']}/{min(5, ds['image_count'])} sample",
                    ds["import_status"],
                    f"{ds['import_progress']}%"
                ])
            
            headers = ["", "Name", "Images", "With Labels", "Import Status", "Progress"]
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
        
        # Execution time
        print(f"\nExecution time: {result['execution_time']:.2f} seconds")
        print("\n" + "="*60)

def main():
    """Main function to run the service checkup."""
    parser = argparse.ArgumentParser(description="Service Checkup for YOLO Dataset Management System")
    parser.add_argument("--url", default=API_URL, help="API URL (default: http://localhost:8000/api/v1)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Request timeout in seconds")
    parser.add_argument("--dataset", help="Dataset ID for detailed report")
    parser.add_argument("--image", help="Image ID for label report (requires --dataset)")
    parser.add_argument("--list-images", action="store_true", help="List images for a dataset (requires --dataset)")
    parser.add_argument("--limit", type=int, default=10, help="Limit for image listing")
    parser.add_argument("--full", action="store_true", help="Run full service checkup")
    
    args = parser.parse_args()
    
    checkup = ServiceCheckup(api_url=args.url, timeout=args.timeout)
    
    if args.full or (not args.dataset and not args.image and not args.list_images):
        # Run full checkup
        checkup.print_full_report()
    elif args.dataset and args.image:
        # Generate label report for a specific image
        print(checkup.generate_label_report(args.dataset, args.image))
    elif args.dataset and args.list_images:
        # Generate image report for a dataset
        print(checkup.generate_image_report(args.dataset, args.limit))
    elif args.dataset:
        # Generate dataset report
        print(checkup.generate_dataset_report(args.dataset))
    else:
        # Generate dataset summary
        checkup.get_datasets()
        print(checkup.generate_dataset_report())

if __name__ == "__main__":
    main()
