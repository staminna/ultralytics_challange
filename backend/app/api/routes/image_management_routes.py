"""
Image Management Routes

Handles operations related to images within datasets.
Extracted from dataset_routes.py for better separation of concerns.
"""

from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from ...schemas.dataset import Image as ImageSchema
from ...schemas.dataset_schema import ImageUpdate, DeleteResponse
from ...services.dataset_service import DatasetService, get_dataset_service

router = APIRouter(prefix="/datasets", tags=["Image Management"])


@router.get("/{dataset_id}/images", response_model=List[ImageSchema])
async def list_dataset_images(
    dataset_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of images to return"),
    offset: int = Query(0, ge=0, description="Number of images to skip"),
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """
    List all images with their labels for a specific dataset.
    
    This endpoint fulfills the core use case: List images with labels for a specific dataset
    """
    try:
        images = await dataset_service.get_images_for_dataset(
            dataset_id=dataset_id,
            skip=offset,
            limit=limit
        )
        return images
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving images: {str(e)}")


@router.get("/{dataset_id}/images/debug")
async def debug_dataset_images(
    dataset_id: str,
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """
    Debug endpoint to check dataset images functionality.
    """
    try:
        dataset = await dataset_service.get_dataset(dataset_id)
        if not dataset:
            return {"error": "Dataset not found", "dataset_id": dataset_id}
        
        images_count = len(dataset.images) if dataset.images else 0
        
        return {
            "dataset_id": dataset_id,
            "dataset_name": dataset.name,
            "images_count": images_count,
            "has_images_field": hasattr(dataset, 'images'),
            "images_field_type": type(dataset.images).__name__ if hasattr(dataset, 'images') else None,
            "first_few_images": [
                {"id": str(img.id), "filename": img.filename} 
                for img in (dataset.images[:3] if dataset.images else [])
            ]
        }
    except Exception as e:
        return {"error": str(e), "dataset_id": dataset_id}


@router.get("/images/{image_id}", response_model=ImageSchema)
async def get_image(
    image_id: str,
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """Get a specific image by ID with its labels and download URL."""
    image = await dataset_service.get_image(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    return image


@router.put("/images/{image_id}", response_model=ImageSchema)
async def update_image(
    image_id: str,
    update_data: ImageUpdate,
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """Update image metadata."""
    try:
        updated_image = await dataset_service.update_image(
            image_id=image_id,
            filename=update_data.filename,
            width=update_data.width,
            height=update_data.height
        )
        if not updated_image:
            raise HTTPException(status_code=404, detail="Image not found")
        return updated_image
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating image: {str(e)}")


@router.delete("/images/{image_id}", response_model=DeleteResponse)
async def delete_image(
    image_id: str,
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """Delete an image and all its labels."""
    success = await dataset_service.delete_image(image_id)
    if not success:
        raise HTTPException(status_code=404, detail="Image not found")
    return DeleteResponse(message="Image deleted successfully")


@router.post("/{dataset_id}/images", response_model=ImageSchema)
async def upload_image_to_dataset(
    dataset_id: str,
    image: UploadFile = File(...),
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """Upload a single image to a dataset."""
    try:
        uploaded_image = await dataset_service.upload_image_to_dataset(dataset_id, image)
        return uploaded_image
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading image: {str(e)}")
