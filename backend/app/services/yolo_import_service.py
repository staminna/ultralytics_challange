"""YOLO Import Service - Refactored

This is a lightweight wrapper around the new orchestrator-based architecture.
Maintains backward compatibility while delegating to focused services.
"""

from typing import Optional
from fastapi import UploadFile
import logging

from ..models.mongo_models import Dataset
from .dataset_import_orchestrator import DatasetImportOrchestrator, get_dataset_import_orchestrator
from .chunked_upload_service import ChunkedUploadService

logger = logging.getLogger(__name__)


class YoloImportService:
    """
    Refactored YOLO Import Service - now delegates to specialized services.
    
    This maintains backward compatibility while using the new orchestrator pattern.
    The heavy lifting is now done by focused services with clear responsibilities.
    """
    
    def __init__(self):
        self.orchestrator = get_dataset_import_orchestrator()
        self.chunked_service = ChunkedUploadService()

    async def import_yolo_dataset(self, file: UploadFile, dataset_name: Optional[str] = None) -> Dataset:
        """Import a YOLO dataset - delegates to orchestrator."""
        return await self.orchestrator.import_yolo_dataset(file, dataset_name)
    
    async def add_chunk_to_dataset(self, dataset_id: str, upload_id: str, chunk_number: int, total_chunks: int, chunk_file: UploadFile):
        """Add a chunk to an existing dataset - delegates to chunked service."""
        return await self.chunked_service.upload_chunk(
            dataset_id=dataset_id,
            upload_id=upload_id, 
            chunk_number=chunk_number,
            total_chunks=total_chunks,
            chunk_file=chunk_file
        )


def get_yolo_import_service() -> YoloImportService:
    """Dependency injection factory"""
    return YoloImportService()
