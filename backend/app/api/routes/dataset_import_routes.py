"""
Dataset Import Routes

Handles dataset import operations including YOLO format imports and chunked uploads.
Extracted from dataset_routes.py for better separation of concerns.
"""

from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ...schemas.dataset_schema import DatasetImportResponse
from ...services.dataset_import_orchestrator import DatasetImportOrchestrator, get_dataset_import_orchestrator
from ...services.yolo_import_service import YoloImportService, get_yolo_import_service

router = APIRouter(prefix="/datasets", tags=["Dataset Import"])


@router.post("/import/yolo", response_model=DatasetImportResponse)
async def import_yolo_dataset(
    file: UploadFile = File(...),
    dataset_name: Optional[str] = Form(None),
    import_orchestrator: DatasetImportOrchestrator = Depends(get_dataset_import_orchestrator)
):
    """
    Import a dataset in YOLO format with enhanced duplicate checking.
    
    This endpoint fulfills the core use case: Import dataset in YOLO format
    
    The uploaded file should be a ZIP archive containing:
    - images/ directory with image files (supports train/val/test subdirectories)
    - labels/ directory with YOLO format label files (.txt)
    - (optional) classes.txt or data.yaml with class definitions
    
    Features:
    - Enhanced duplicate detection with name variations
    - Local storage fallback when GCP credentials unavailable
    - Comprehensive YOLO dataset structure validation
    - Automatic cleanup on import failure
    """
    try:
        dataset = await import_orchestrator.import_yolo_dataset(file, dataset_name)
        
        # Create concise response
        return DatasetImportResponse(
            id=str(dataset.id),
            name=dataset.name,
            description=dataset.description,
            format=dataset.format,
            file_hash=dataset.file_hash,
            processing_status="completed",
            images_count=len(dataset.images) if dataset.images else 0,
            labels_count=sum(len(img.labels) for img in dataset.images if img.labels) if dataset.images else 0,
            processed_images=len(dataset.images) if dataset.images else 0,
            classes_count=len(set(label.class_id for img in dataset.images if img.labels for label in img.labels)) if dataset.images else 0,
            original_filename=file.filename
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/{dataset_id}/chunks")
async def upload_chunk(
    dataset_id: str,
    upload_id: str,
    chunk_number: int,
    total_chunks: int,
    chunk_file: UploadFile = File(...),
    yolo_import_service: YoloImportService = Depends(get_yolo_import_service)
):
    """
    Upload a chunk of a large dataset in YOLO format.
    
    This endpoint supports the core use case: Import dataset in YOLO format,
    specifically for large datasets up to 100GB.
    
    Parameters:
    - dataset_id: ID of the dataset to add the chunk to
    - upload_id: Upload ID from a previous initiate request
    - chunk_number: Index of this chunk (0-based)
    - total_chunks: Total number of chunks expected
    - chunk_file: Binary data for this chunk
    """
    try:
        result = await yolo_import_service.add_chunk_to_dataset(
            dataset_id=dataset_id,
            upload_id=upload_id,
            chunk_number=chunk_number,
            total_chunks=total_chunks,
            chunk_file=chunk_file
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chunk upload failed: {str(e)}")


@router.get("/{dataset_id}/import-status")
async def get_import_status(
    dataset_id: str,
    import_orchestrator: DatasetImportOrchestrator = Depends(get_dataset_import_orchestrator)
):
    """
    Get the status of a dataset import.
    
    This endpoint supports the core use case: Import dataset in YOLO format,
    by allowing clients to check the progress of large dataset imports.
    """
    try:
        status = await import_orchestrator.get_import_status(dataset_id)
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting import status: {str(e)}")
