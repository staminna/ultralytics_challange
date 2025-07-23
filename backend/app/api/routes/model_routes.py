"""
API routes for YOLOv8-X model functionality.

This module includes endpoints for:
1. Running inference on uploaded images
2. Auto-annotating datasets
3. Fine-tuning models on custom datasets
"""

from typing import Any, Dict, List, Optional

from fastapi import (APIRouter, BackgroundTasks, Depends, File, Form,
                     HTTPException, UploadFile)
from pydantic import BaseModel

from ...schemas.dataset import Dataset, Image, Label
from ...services.yolo_model_service import YOLOModelService

# Create router
router = APIRouter(prefix="/models", tags=["models"])

# Models for request/response
class ModelPredictionResponse(BaseModel):
    detections: List[Dict[str, Any]]
    
class AutoAnnotateRequest(BaseModel):
    confidence: float = 0.25
    class_filter: Optional[List[int]] = None
    
class FineTuneRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    dataset_id: str
    model_name: str
    epochs: int = 10
    batch_size: int = 16
    
class ModelJobResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    status: str
    model_id: Optional[str] = None
    dataset_id: Optional[str] = None
    message: str
    
# Dependency to get model service
def get_yolo_model_service():
    return YOLOModelService()

@router.post("/predict", response_model=ModelPredictionResponse)
async def predict_image(
    confidence: float = Form(0.25),
    image: UploadFile = File(...),
    model_service: YOLOModelService = Depends(get_yolo_model_service)
):
    """
    Run YOLOv8-X object detection on an uploaded image.
    
    Args:
        confidence: Confidence threshold for detections (0.0-1.0)
        image: Image file to run detection on
        
    Returns:
        JSON response with detected objects
    """
    # Read image
    image_data = await image.read()
    
    # Run prediction
    detections = await model_service.predict(
        image_data=image_data,
        confidence=confidence
    )
    
    return ModelPredictionResponse(detections=detections)

@router.post("/auto-annotate/image/{image_id}", response_model=List[Label])
async def auto_annotate_image(
    image_id: str,
    confidence: float = 0.25,
    class_filter: Optional[List[int]] = None,
    model_service: YOLOModelService = Depends(get_yolo_model_service)
):
    """
    Auto-annotate an image using YOLOv8-X.
    
    Args:
        image_id: ID of the image to annotate
        confidence: Confidence threshold for detections
        class_filter: Optional list of class IDs to include
        
    Returns:
        List of created label objects
    """
    return await model_service.auto_annotate_image(
        image_id=image_id,
        confidence=confidence,
        class_filter=class_filter
    )

@router.post("/auto-annotate/dataset/{dataset_id}", response_model=ModelJobResponse)
async def auto_annotate_dataset(
    dataset_id: str,
    background_tasks: BackgroundTasks,
    request: AutoAnnotateRequest,
    model_service: YOLOModelService = Depends(get_yolo_model_service)
):
    """
    Auto-annotate an entire dataset using YOLOv8-X.
    
    Args:
        dataset_id: ID of the dataset to annotate
        background_tasks: FastAPI background tasks object
        request: Auto-annotation request parameters
        
    Returns:
        Job status information
    """
    result = await model_service.auto_annotate_dataset(
        dataset_id=dataset_id,
        background_tasks=background_tasks,
        confidence=request.confidence,
        class_filter=request.class_filter
    )
    
    return ModelJobResponse(**result)

@router.post("/fine-tune", response_model=ModelJobResponse)
async def fine_tune_model(
    background_tasks: BackgroundTasks,
    request: FineTuneRequest,
    model_service: YOLOModelService = Depends(get_yolo_model_service)
):
    """
    Fine-tune YOLOv8-X model on a custom dataset.
    
    Args:
        background_tasks: FastAPI background tasks object
        request: Fine-tuning request parameters
        
    Returns:
        Job status information
    """
    result = await model_service.fine_tune_model(
        dataset_id=request.dataset_id,
        epochs=request.epochs,
        batch_size=request.batch_size,
        background_tasks=background_tasks,
        model_name=request.model_name
    )
    
    return ModelJobResponse(**result)

@router.get("/status/{model_id}")
async def get_model_status(
    model_id: str,
    model_service: YOLOModelService = Depends(get_yolo_model_service)
):
    """
    Get status of a model.
    
    Args:
        model_id: ID of the model
        
    Returns:
        Model status information
    """
    # Get model from Firestore
    model_ref = model_service.db.collection(model_service.MODEL_COLLECTION).document(model_id)
    model_doc = model_ref.get()
    
    if not model_doc.exists:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")
    
    return model_doc.to_dict()
