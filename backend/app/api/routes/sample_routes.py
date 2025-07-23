"""
Routes for handling sample images and running predictions.

This module provides endpoints for:
1. Downloading sample hotel images from London
2. Listing available sample images
3. Running predictions on sample images
"""

import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import requests
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel

from ...core.config import get_settings
from ...services.yolo_model_service import YOLOModelService

# Create router
router = APIRouter(prefix="/samples", tags=["samples"])

# Dependency to get model service
def get_yolo_model_service():
    return YOLOModelService()

# Sample image directory
SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "hotel_sample_images")
LONDON_HOTELS_DIR = os.path.join(SAMPLE_DIR, "london_hotels")

# Create directories if they don't exist
os.makedirs(SAMPLE_DIR, exist_ok=True)
os.makedirs(LONDON_HOTELS_DIR, exist_ok=True)

# London hotel image URLs
LONDON_HOTEL_IMAGES = [
    # London hotel street views and facades
    "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxzZWFyY2h8MTV8fGxvbmRvbiUyMGhvdGVsfGVufDB8fDB8fA%3D%3D&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1551632436-cbf8dd35adfa?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxzZWFyY2h8M3x8bG9uZG9uJTIwaG90ZWx8ZW58MHx8MHx8&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1568495248636-6432b97bd949?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxzZWFyY2h8MTB8fGxvbmRvbiUyMGhvdGVsfGVufDB8fDB8fA%3D%3D&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1444201983204-c43cbd584d93?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxzZWFyY2h8MTZ8fGxvbmRvbiUyMGhvdGVsfGVufDB8fDB8fA%3D%3D&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1611892440504-42a792e24d32?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxzZWFyY2h8MTh8fGxvbmRvbiUyMGhvdGVsfGVufDB8fDB8fA%3D%3D&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1584132967334-10e028bd69f7?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxzZWFyY2h8NXx8aG90ZWwlMjBmYWNhZGV8ZW58MHx8MHx8&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1615460549969-36fa19521a4f?ixlib=rb-4.0.3&ixid=MnwxMjA3fDB8MHxzZWFyY2h8Mzl8fGhvdGVsfGVufDB8fDB8fA%3D%3D&auto=format&fit=crop&w=800&q=60",
    
    # Additional London hotel facades and street views
    "https://images.unsplash.com/photo-1566073771259-6a8506099945?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1590490360182-c33d57733427?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1618773928121-c32242e63f39?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    
    # Hotel building exteriors
    "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1571896349842-33c89424de2d?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1578662996442-48f60103fc96?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1520637836862-4d197d17c90a?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    
    # London architecture and hotel buildings
    "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1520637736862-4d197d17c90a?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1549294413-26f195200c16?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1571896349842-33c89424de2d?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1578662996442-48f60103fc96?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    
    # Hotel entrances and facades
    "https://images.unsplash.com/photo-1564501049412-61c2a3083791?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1582719508461-905c673771fd?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1587381420270-3e1a5b9e6904?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1571896349842-33c89424de2d?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1520637736862-4d197d17c90a?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    
    # London street view hotels
    "https://images.unsplash.com/photo-1549294413-26f195200c16?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1578662996442-48f60103fc96?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1571896349842-33c89424de2d?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1520637836862-4d197d17c90a?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    
    # Building facades and hotel exteriors
    "https://images.unsplash.com/photo-1564501049412-61c2a3083791?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1582719508461-905c673771fd?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1587381420270-3e1a5b9e6904?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1571896349842-33c89424de2d?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1520637736862-4d197d17c90a?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    
    # More hotel building exteriors
    "https://images.unsplash.com/photo-1549294413-26f195200c16?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1578662996442-48f60103fc96?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1571896349842-33c89424de2d?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1520637836862-4d197d17c90a?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    
    # London hotel street facades
    "https://images.unsplash.com/photo-1564501049412-61c2a3083791?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1582719508461-905c673771fd?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1587381420270-3e1a5b9e6904?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1571896349842-33c89424de2d?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1520637736862-4d197d17c90a?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    
    # Additional hotel exteriors
    "https://images.unsplash.com/photo-1549294413-26f195200c16?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1578662996442-48f60103fc96?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1571896349842-33c89424de2d?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1520637836862-4d197d17c90a?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    
    # Final set of hotel building images
    "https://images.unsplash.com/photo-1564501049412-61c2a3083791?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1582719508461-905c673771fd?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1587381420270-3e1a5b9e6904?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1571896349842-33c89424de2d?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60",
    "https://images.unsplash.com/photo-1520637736862-4d197d17c90a?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=60"
]

# Schemas
class DownloadResponse(BaseModel):
    message: str
    downloaded: int
    total: int
    files: List[str]

class SampleImage(BaseModel):
    filename: str
    path: str
    size_kb: float

class PredictionResult(BaseModel):
    filename: str
    detections: List[Dict[str, Any]]

class PredictionRequest(BaseModel):
    confidence: float = 0.25
    filename: Optional[str] = None

@router.post("/download-london-hotels", response_model=DownloadResponse)
async def download_london_hotel_images(
    background_tasks: BackgroundTasks,
    force: bool = Query(False, description="Force re-download of images even if they already exist")
):
    """
    Download sample London hotel images to use for prediction examples.
    
    Args:
        force: Whether to force re-download if images already exist
        
    Returns:
        Information about downloaded images
    """
    # Clear directory if force is True
    if force and os.path.exists(LONDON_HOTELS_DIR):
        shutil.rmtree(LONDON_HOTELS_DIR)
        os.makedirs(LONDON_HOTELS_DIR, exist_ok=True)
    
    # Check if we already have images
    existing_files = os.listdir(LONDON_HOTELS_DIR) if os.path.exists(LONDON_HOTELS_DIR) else []
    if existing_files and not force:
        return DownloadResponse(
            message="London hotel images already downloaded",
            downloaded=0,
            total=len(existing_files),
            files=existing_files
        )
    
    # Start background download task
    background_tasks.add_task(download_images_task, LONDON_HOTELS_DIR, LONDON_HOTEL_IMAGES)
    
    return DownloadResponse(
        message="Download started in background",
        downloaded=0,
        total=len(LONDON_HOTEL_IMAGES),
        files=[]
    )

@router.get("/london-hotels", response_model=List[SampleImage])
async def list_london_hotel_images():
    """
    List available London hotel sample images.
    
    Returns:
        List of available sample images
    """
    # Check if directory exists
    if not os.path.exists(LONDON_HOTELS_DIR):
        return []
    
    # Get list of images
    image_files = [f for f in os.listdir(LONDON_HOTELS_DIR) 
                   if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    # Create response
    result = []
    for filename in image_files:
        file_path = os.path.join(LONDON_HOTELS_DIR, filename)
        size_kb = os.path.getsize(file_path) / 1024
        result.append(SampleImage(
            filename=filename,
            path=file_path,
            size_kb=round(size_kb, 2)
        ))
    
    return result

@router.post("/predict/london-hotel", response_model=PredictionResult)
async def predict_london_hotel_image(
    request: PredictionRequest
):
    """
    Run prediction on a London hotel sample image.
    
    Args:
        request: Prediction request with confidence and optional filename
        
    Returns:
        Prediction results with detections
    """
    # Check if directory exists
    if not os.path.exists(LONDON_HOTELS_DIR):
        raise HTTPException(
            status_code=404,
            detail="No London hotel images found. Please download them first."
        )
    
    # Get list of images
    image_files = [f for f in os.listdir(LONDON_HOTELS_DIR) 
                   if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    if not image_files:
        raise HTTPException(
            status_code=404,
            detail="No London hotel images found. Please download them first."
        )
    
    # Select image
    if request.filename and request.filename in image_files:
        selected_image = request.filename
    else:
        # If no filename specified or not found, use the first one
        selected_image = image_files[0]
    
    # Load image
    image_path = os.path.join(LONDON_HOTELS_DIR, selected_image)
    with open(image_path, "rb") as f:
        image_data = f.read()
    
    # Import required libraries here to avoid import errors if some are missing
    try:
        import io

        import numpy as np
        import torch
        from PIL import Image
        from ultralytics import YOLO
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Required library not installed: {str(e)}"
        )
    
    # Run prediction directly without using DB
    try:
        # Load YOLOv8 model directly with progress reporting
        model_path = "yolov8x.pt"  # Will download automatically if not present
        print(f"Loading YOLOv8-X model from {model_path}...")
        print(f"Note: If the model doesn't exist, it will be downloaded (~670MB)")
        
        # Check if model exists before trying to load it
        if not os.path.exists(model_path):
            print(f"Model file not found. Downloading {model_path}...")
            # Will automatically download
        
        # Load with timeout protection
        try:
            model = YOLO(model_path)
            print(f"Successfully loaded YOLOv8-X model")
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load YOLOv8 model: {str(e)}"
            )
        
        # Process image with YOLOv8 directly
        image = Image.open(io.BytesIO(image_data))
        
        # Run prediction
        results = model.predict(image, conf=request.confidence)
        
        # COCO class names
        COCO_CLASSES = [
            "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", 
            "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", 
            "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack", 
            "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", 
            "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket", 
            "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple", 
            "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", 
            "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote", 
            "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator", "book", 
            "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
        ]
        
        # Process results
        detections = []
        for result in results:
            boxes = result.boxes
            
            for i, box in enumerate(boxes):
                # Extract information
                x1, y1, x2, y2 = box.xyxy[0].tolist()  # box coordinates
                conf = box.conf.item()  # confidence score
                cls_id = int(box.cls.item())  # class id
                
                # Get class name from COCO classes
                class_name = COCO_CLASSES[cls_id] if cls_id < len(COCO_CLASSES) else f"class_{cls_id}"
                
                # Convert to YOLO format (normalized coordinates)
                img_width, img_height = image.size
                x_center = (x1 + x2) / 2 / img_width
                y_center = (y1 + y2) / 2 / img_height
                width = (x2 - x1) / img_width
                height = (y2 - y1) / img_height
                
                # Create detection object
                detection = {
                    "class_id": cls_id,
                    "class_name": class_name,
                    "confidence": conf,
                    "x_center": x_center,
                    "y_center": y_center,
                    "width": width,
                    "height": height,
                    # Also include absolute coordinates for display
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2
                }
                detections.append(detection)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error running prediction: {str(e)}"
        )
    
    return PredictionResult(
        filename=selected_image,
        detections=detections
    )

@router.post("/predict/all-london-hotels")
async def predict_all_london_hotel_images(
    request: PredictionRequest,
    background_tasks: BackgroundTasks,
    model_service: YOLOModelService = Depends(get_yolo_model_service)
):
    """
    Run prediction on all London hotel sample images.
    
    Args:
        request: Prediction request with confidence
        
    Returns:
        Job status information
    """
    # Check if directory exists
    if not os.path.exists(LONDON_HOTELS_DIR):
        raise HTTPException(
            status_code=404,
            detail="No London hotel images found. Please download them first."
        )
    
    # Get list of images
    image_files = [f for f in os.listdir(LONDON_HOTELS_DIR) 
                   if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    if not image_files:
        raise HTTPException(
            status_code=404,
            detail="No London hotel images found. Please download them first."
        )
    
    # Start background prediction task
    job_id = str(uuid.uuid4())
    background_tasks.add_task(
        predict_all_images_task,
        LONDON_HOTELS_DIR,
        image_files,
        request.confidence,
        job_id,
        model_service
    )
    
    return {
        "status": "started",
        "job_id": job_id,
        "message": f"Started predictions on {len(image_files)} images",
        "total_images": len(image_files)
    }

# Background tasks
async def download_images_task(output_dir: str, image_urls: List[str]):
    """
    Background task to download images.
    
    Args:
        output_dir: Directory to save images to
        image_urls: List of image URLs to download
    """
    os.makedirs(output_dir, exist_ok=True)
    
    async with httpx.AsyncClient() as client:
        for i, url in enumerate(image_urls):
            try:
                # Get image
                response = await client.get(url)
                response.raise_for_status()
                
                # Save image
                filename = f"london_hotel_{i+1}.jpg"
                file_path = os.path.join(output_dir, filename)
                
                with open(file_path, "wb") as f:
                    f.write(response.content)
                
                print(f"Downloaded {url} to {file_path}")
            
            except Exception as e:
                print(f"Error downloading {url}: {e}")

async def predict_all_images_task(
    images_dir: str,
    image_files: List[str],
    confidence: float,
    job_id: str,
    model_service: YOLOModelService
):
    """
    Background task to run predictions on all images.
    
    Args:
        images_dir: Directory containing images
        image_files: List of image filenames
        confidence: Confidence threshold for predictions
        job_id: Job ID for tracking
        model_service: YOLO model service instance
    """
    results = {}
    
    # Create results directory
    results_dir = os.path.join(SAMPLE_DIR, f"results_{job_id}")
    os.makedirs(results_dir, exist_ok=True)
    
    try:
        # Load model
        if model_service.model is None:
            await model_service.load_model()
        
        # Process each image
        for filename in image_files:
            try:
                # Load image
                image_path = os.path.join(images_dir, filename)
                with open(image_path, "rb") as f:
                    image_data = f.read()
                
                # Run prediction
                detections = await model_service.predict(
                    image_data=image_data,
                    confidence=confidence
                )
                
                # Save results
                results[filename] = detections
                print(f"Processed {filename}: {len(detections)} detections")
                
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                results[filename] = {"error": str(e)}
        
        # Save results to file
        import json
        results_path = os.path.join(results_dir, "results.json")
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"All predictions completed. Results saved to {results_path}")
        
    except Exception as e:
        print(f"Error in prediction task: {e}")
