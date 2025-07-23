from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status

from ....services.dataset_service import DatasetService, get_dataset_service
from ....services.yolo_import_service import YoloImportService, get_yolo_import_service
from ....models.mongo_models import Dataset, Image
from ....schemas.dataset_schema import DatasetCreate, DatasetImportResponse

router = APIRouter()

@router.post("/datasets/", response_model=Dataset, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    dataset: DatasetCreate,
    service: DatasetService = Depends(get_dataset_service)
):
    return await service.create_dataset(dataset)

@router.get("/datasets/", response_model=List[Dataset])
async def list_datasets(
    skip: int = 0,
    limit: int = 10,
    service: DatasetService = Depends(get_dataset_service)
):
    return await service.get_datasets(skip=skip, limit=limit)

@router.get("/datasets/{dataset_id}", response_model=Dataset)
async def get_dataset(
    dataset_id: UUID,
    service: DatasetService = Depends(get_dataset_service)
):
    dataset = await service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return dataset

@router.delete("/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: UUID,
    service: DatasetService = Depends(get_dataset_service)
):
    await service.delete_dataset(dataset_id)
    return

@router.get("/datasets/{dataset_id}/images", response_model=List[Image])
async def list_images_for_dataset(
    dataset_id: UUID,
    skip: int = 0,
    limit: int = 10,
    service: DatasetService = Depends(get_dataset_service)
):
    return await service.get_images_for_dataset(dataset_id, skip=skip, limit=limit)

@router.post("/datasets/import/yolo", response_model=DatasetImportResponse)
async def import_yolo_dataset(
    file: UploadFile = File(...),
    dataset_name: Optional[str] = Form(None),
    service: YoloImportService = Depends(get_yolo_import_service)
):
    """Import a YOLO dataset from ZIP file. Supports datasets up to 100GB with chunked processing."""
    return await service.import_yolo_dataset(file=file, dataset_name=dataset_name)

@router.get("/datasets/{dataset_id}/import/status")
async def get_import_status(
    dataset_id: UUID,
    service: DatasetService = Depends(get_dataset_service)
):
    """Get the import/processing status of a dataset."""
    dataset = await service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    
    metadata = dataset.metadata or {}
    return {
        "dataset_id": str(dataset.id),
        "dataset_name": dataset.name,
        "processing_status": metadata.get("processing_status", "unknown"),
        "processed_images": metadata.get("processed_images", 0),
        "total_images": metadata.get("images_count", 0),
        "error_message": metadata.get("error_message"),
        "import_summary": metadata.get("import_summary")
    }
