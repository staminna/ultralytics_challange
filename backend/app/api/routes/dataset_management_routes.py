"""
Dataset Management Routes

Handles CRUD operations for datasets.
Extracted from dataset_routes.py for better separation of concerns.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query

from ...schemas.dataset import Dataset as DatasetSchema
from ...schemas.dataset_schema import DatasetCreate, DeleteResponse
from ...services.dataset_service import DatasetService, get_dataset_service

router = APIRouter(prefix="/datasets", tags=["Dataset Management"])


@router.post("/", response_model=DatasetSchema)
async def create_dataset(
    dataset_data: DatasetCreate,
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """Create a new dataset."""
    return await dataset_service.create_dataset(dataset_data)


@router.get("/", response_model=List[DatasetSchema])
async def list_datasets(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of datasets to return"),
    offset: int = Query(0, ge=0, description="Number of datasets to skip"),
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """
    List all datasets with pagination.
    
    This endpoint fulfills the core use case: List datasets
    """
    try:
        datasets = await dataset_service.get_datasets(skip=offset, limit=limit)
        return datasets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving datasets: {str(e)}")


@router.get("/{dataset_id}", response_model=DatasetSchema)
async def get_dataset(
    dataset_id: str,
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """Get a dataset by ID."""
    dataset_model = await dataset_service.get_dataset(dataset_id)
    # Convert model to schema
    return dataset_service._convert_to_schema(dataset_model)


@router.delete("/{dataset_id}", response_model=DeleteResponse)
async def delete_dataset(
    dataset_id: str,
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """Delete a dataset and all its images and labels."""
    try:
        success = await dataset_service.delete_dataset(dataset_id)
        if not success:
            raise HTTPException(status_code=404, detail="Dataset not found")
        return DeleteResponse(message="Dataset deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting dataset: {str(e)}")
