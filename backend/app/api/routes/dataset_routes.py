from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Query
from typing import List, Optional, Dict, Any

from ...services.dataset_service import DatasetService
from ...services.yolo_import_service import YoloImportService
from ...schemas.dataset import (
    Dataset, DatasetCreate, DatasetListResponse,
    ImageListResponse, YoloImportRequest
)
from ...core.gcp import get_storage_bucket
import tempfile
import zipfile
import json
import os
from datetime import datetime

router = APIRouter(prefix="/datasets", tags=["datasets"])

# Service dependencies
def get_dataset_service():
    return DatasetService()

def get_yolo_import_service():
    return YoloImportService()


@router.post("/", response_model=Dataset, status_code=201)
async def create_dataset(
    dataset_data: DatasetCreate,
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """Create a new dataset."""
    return await dataset_service.create_dataset(dataset_data)


@router.get("/", response_model=DatasetListResponse)
async def list_datasets(
    limit: int = 100,
    offset: int = 0,
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """
    List all datasets with pagination.
    
    This endpoint fulfills the core use case: List datasets
    """
    datasets, total = await dataset_service.list_datasets(limit=limit, offset=offset)
    return {
        "datasets": datasets,
        "total": total
    }


@router.get("/{dataset_id}", response_model=Dataset)
async def get_dataset(
    dataset_id: str,
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """Get a dataset by ID."""
    dataset = await dataset_service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.get("/{dataset_id}/images", response_model=ImageListResponse)
async def list_dataset_images(
    dataset_id: str,
    limit: int = 100,
    offset: int = 0,
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """
    List all images with their labels for a specific dataset.
    
    This endpoint fulfills the core use case: List images with labels for a specific dataset
    """
    images, total = await dataset_service.get_images_for_dataset(
        dataset_id=dataset_id, 
        limit=limit,
        offset=offset
    )
    
    return {
        "images": images,
        "total": total,
        "dataset_id": dataset_id
    }


@router.post("/import/yolo", response_model=Dataset)
async def import_yolo_dataset(
    background_tasks: BackgroundTasks,
    dataset_name: str = Form(...),
    description: Optional[str] = Form(None),
    class_names: Optional[List[str]] = Form([]),
    zip_file: UploadFile = File(...),
    yolo_import_service: YoloImportService = Depends(get_yolo_import_service)
):
    """
    Import a dataset in YOLO format.
    
    This endpoint fulfills the core use case: Import dataset in YOLO format
    
    The uploaded file should be a ZIP archive containing:
    - images/ directory with image files
    - labels/ directory with YOLO format label files (.txt)
    - (optional) classes.txt with class names
    
    For large datasets (>100MB), the upload will be processed asynchronously.
    """
    if not zip_file.filename.endswith('.zip'):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must be a ZIP archive"
        )
        
    return await yolo_import_service.import_yolo_dataset(
        dataset_name=dataset_name,
        description=description,
        zip_file=zip_file,
        class_names=class_names,
        background_tasks=background_tasks
    )


@router.post("/import/yolo/chunk", response_model=Dict[str, Any])
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
    return await yolo_import_service.add_chunk_to_dataset(
        dataset_id=dataset_id,
        upload_id=upload_id,
        chunk_number=chunk_number,
        total_chunks=total_chunks,
        chunk_file=chunk_file
    )


@router.get("/import/status/{dataset_id}", response_model=Dict[str, Any])
async def get_import_status(
    dataset_id: str,
    yolo_import_service: YoloImportService = Depends(get_yolo_import_service)
):
    """
    Get the status of a dataset import.
    
    This endpoint supports the core use case: Import dataset in YOLO format,
    by allowing clients to check the progress of large dataset imports.
    """
    return await yolo_import_service.get_import_status(dataset_id)


@router.post("/upload/storage-only")
async def upload_dataset_storage_only(
    dataset_name: str = Form(...),
    description: Optional[str] = Form(None),
    class_names: Optional[List[str]] = Form([]),
    zip_file: UploadFile = File(...)
):
    """
    Upload dataset directly to Cloud Storage without Firestore.
    Temporary solution for Datastore Mode projects.
    """
    try:
        if not zip_file.filename.endswith('.zip'):
            raise HTTPException(status_code=400, detail="File must be a ZIP archive")
        
        # Get storage bucket
        bucket = get_storage_bucket()
        
        # Create metadata
        metadata = {
            "dataset_name": dataset_name,
            "description": description,
            "class_names": class_names,
            "uploaded_at": datetime.utcnow().isoformat(),
            "original_filename": zip_file.filename
        }
        
        # Upload zip file to storage
        zip_blob_name = f"datasets/{dataset_name}/{zip_file.filename}"
        zip_blob = bucket.blob(zip_blob_name)
        
        # Read and upload file content
        file_content = await zip_file.read()
        zip_blob.upload_from_string(file_content, content_type='application/zip')
        
        # Upload metadata as JSON
        metadata_blob_name = f"datasets/{dataset_name}/metadata.json"
        metadata_blob = bucket.blob(metadata_blob_name)
        metadata_blob.upload_from_string(
            json.dumps(metadata, indent=2), 
            content_type='application/json'
        )
        
        # Extract and upload individual files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save zip to temp file
            temp_zip_path = f"{temp_dir}/dataset.zip"
            with open(temp_zip_path, 'wb') as f:
                f.write(file_content)
            
            # Extract and upload contents
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                
                # Upload extracted files
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file != 'dataset.zip':
                            file_path = os.path.join(root, file)
                            relative_path = os.path.relpath(file_path, temp_dir)
                            
                            blob_name = f"datasets/{dataset_name}/extracted/{relative_path}"
                            blob = bucket.blob(blob_name)
                            blob.upload_from_filename(file_path)
        
        return {
            "status": "success",
            "message": f"Dataset '{dataset_name}' uploaded to Cloud Storage",
            "bucket": bucket.name,
            "zip_path": zip_blob_name,
            "metadata_path": metadata_blob_name,
            "class_names": class_names,
            "files_uploaded": len(class_names)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
