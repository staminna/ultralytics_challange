import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.schemas.dataset_schemas import (DatasetCreate, DatasetImportYOLO,
                                         DatasetListResponse, DatasetResponse,
                                         ImageListResponse,
                                         ImportStatusResponse,
                                         PaginationParams)
from app.services.dataset_service import dataset_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(dataset: DatasetCreate):
    """Create a new dataset"""
    try:
        return await dataset_service.create_dataset(dataset.model_dump())
    except Exception as e:
        logger.error(f"Error creating dataset: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create dataset"
        )

@router.get("/", response_model=DatasetListResponse)
async def list_datasets(
    skip: int = 0,
    limit: int = 100
):
    """List all datasets with pagination."""
    try:
        datasets, total = await dataset_service.list_datasets(skip=skip, limit=limit)
        return {
            "datasets": datasets,
            "total": total
        }
    except Exception as e:
        logger.error(f"Error listing datasets: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: str):
    """Get a specific dataset by ID."""
    dataset = await dataset_service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset

@router.get("/{dataset_id}/images", response_model=ImageListResponse)
async def list_dataset_images(
    dataset_id: str,
    skip: int = 0,
    limit: int = 100
):
    """List all images for a specific dataset with pagination."""
    try:
        images, total = await dataset_service.get_images_for_dataset(
            dataset_id=dataset_id,
            skip=skip,
            limit=limit
        )
        return {
            "images": images,
            "total": total,
            "dataset_id": dataset_id
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing images for dataset {dataset_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/import/yolo", response_model=DatasetResponse, status_code=status.HTTP_202_ACCEPTED)
async def import_yolo_dataset(
    file: UploadFile = File(...),
    dataset_name: str = Form(...),
    description: Optional[str] = Form(None),
    is_public: bool = Form(False)
):
    """Import a YOLO format dataset from a ZIP file"""
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only ZIP files are supported")
    
    try:
        return await dataset_service.import_yolo_dataset(
            file=file,
            dataset_name=dataset_name,
            description=description,
            is_public=is_public
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error importing YOLO dataset: {str(e)}")
        raise HTTPException(status_code=500, detail="Error importing dataset")

@router.get("/{dataset_id}/import/status", response_model=ImportStatusResponse)
async def get_import_status(dataset_id: str):
    """Check the status of a dataset import."""
    # This is a placeholder - implement actual import status tracking
    return {
        "status": "completed",
        "progress": 100,
        "message": "Import completed successfully",
        "dataset_id": dataset_id
    }
