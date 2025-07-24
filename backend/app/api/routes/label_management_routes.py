"""
Label Management Routes

Handles operations related to labels and annotations.
Extracted from dataset_routes.py for better separation of concerns.
"""

from fastapi import APIRouter, Depends, HTTPException

from ...schemas.dataset import Label as LabelSchema
from ...schemas.dataset_schema import LabelCreate, LabelUpdate, DeleteResponse
from ...services.dataset_service import DatasetService, get_dataset_service

router = APIRouter(tags=["Label Management"])


@router.get("/labels/{label_id}", response_model=LabelSchema)
async def get_label(
    label_id: str,
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """Get a specific label by ID."""
    label = await dataset_service.get_label(label_id)
    if not label:
        raise HTTPException(status_code=404, detail="Label not found")
    return label


@router.put("/labels/{label_id}", response_model=LabelSchema)
async def update_label(
    label_id: str,
    update_data: LabelUpdate,
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """Update a label."""
    try:
        updated_label = await dataset_service.update_label(
            label_id=label_id,
            class_id=update_data.class_id,
            x_center=update_data.x_center,
            y_center=update_data.y_center,
            width=update_data.width,
            height=update_data.height
        )
        if not updated_label:
            raise HTTPException(status_code=404, detail="Label not found")
        return updated_label
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating label: {str(e)}")


@router.delete("/labels/{label_id}", response_model=DeleteResponse)
async def delete_label(
    label_id: str,
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """Delete a label."""
    success = await dataset_service.delete_label(label_id)
    if not success:
        raise HTTPException(status_code=404, detail="Label not found")
    return DeleteResponse(message="Label deleted successfully")


@router.post("/images/{image_id}/labels", response_model=LabelSchema)
async def create_label_for_image(
    image_id: str,
    label_data: LabelCreate,
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """Create a label for an image."""
    try:
        label = await dataset_service.create_label(image_id, label_data)
        return label
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating label: {str(e)}")
