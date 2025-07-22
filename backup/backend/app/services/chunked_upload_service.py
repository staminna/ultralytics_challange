"""
Chunked upload service for handling large dataset uploads (up to 100GB).
"""
import io
import json
import os
import tempfile
import uuid
from typing import BinaryIO, Dict, List, Optional

from fastapi import HTTPException, UploadFile
from google.cloud import storage

from ..core.config import get_settings
from ..core.gcp import get_storage_bucket, get_storage_client

# Settings
settings = get_settings()


class ChunkedUploadService:
    """
    Service for handling chunked uploads of large datasets.
    Allows uploading datasets in parts to support files up to 100GB.
    """
    
    def __init__(self):
        self.bucket = get_storage_bucket()
        self.storage_client = get_storage_client()
    
    async def initiate_chunked_upload(self, filename: str, total_size: int) -> Dict:
        """
        Initiate a chunked upload process.
        
        Args:
            filename: Original filename
            total_size: Total size in bytes
            
        Returns:
            Dict containing upload_id and other metadata
        """
        upload_id = str(uuid.uuid4())
        temp_folder = f"uploads/temp/{upload_id}"
        
        # Create metadata file
        metadata = {
            "upload_id": upload_id,
            "filename": filename,
            "total_size": total_size,
            "chunks_received": 0,
            "temp_folder": temp_folder,
            "status": "initiated",
            "created_at": str(self._get_timestamp()),
        }
        
        # Store metadata in cloud storage
        metadata_blob = self.bucket.blob(f"{temp_folder}/metadata.json")
        metadata_blob.upload_from_string(
            json.dumps(metadata),
            content_type="application/json"
        )
        
        return metadata
    
    async def upload_chunk(self, upload_id: str, chunk_number: int, 
                         total_chunks: int, chunk_data: UploadFile) -> Dict:
        """
        Upload a chunk of data for an existing upload.
        
        Args:
            upload_id: ID from initiate_chunked_upload
            chunk_number: Index of current chunk (0-based)
            total_chunks: Total number of chunks expected
            chunk_data: Binary data for this chunk
            
        Returns:
            Dict with updated upload status
        """
        # Get metadata
        metadata = await self._get_upload_metadata(upload_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        if metadata["status"] == "completed":
            raise HTTPException(status_code=400, detail="Upload already completed")
            
        # Upload chunk
        temp_folder = metadata["temp_folder"]
        chunk_blob = self.bucket.blob(f"{temp_folder}/chunk_{chunk_number}")
        
        # Read chunk data
        file_content = await chunk_data.read()
        chunk_blob.upload_from_string(file_content)
        
        # Update metadata
        chunks_received = metadata.get("chunks_received", 0) + 1
        metadata["chunks_received"] = chunks_received
        metadata["last_updated"] = str(self._get_timestamp())
        
        # If all chunks received, mark as ready for finalization
        if chunks_received >= total_chunks:
            metadata["status"] = "ready_for_finalization"
        
        # Update metadata in storage
        metadata_blob = self.bucket.blob(f"{temp_folder}/metadata.json")
        metadata_blob.upload_from_string(
            json.dumps(metadata),
            content_type="application/json"
        )
        
        return metadata
    
    async def finalize_chunked_upload(self, upload_id: str) -> Dict:
        """
        Finalize a chunked upload by combining all chunks into a single file.
        
        Args:
            upload_id: ID from initiate_chunked_upload
            
        Returns:
            Dict with final upload location and metadata
        """
        metadata = await self._get_upload_metadata(upload_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Upload not found")
            
        if metadata["status"] not in ["ready_for_finalization", "completed"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Upload not ready for finalization. Status: {metadata['status']}"
            )
            
        if metadata["status"] == "completed":
            return metadata  # Already finalized
        
        # Combine chunks into a single file
        temp_folder = metadata["temp_folder"]
        filename = metadata["filename"]
        final_path = f"uploads/{upload_id}/{filename}"
        
        # List all chunks
        blobs = list(self.bucket.list_blobs(prefix=f"{temp_folder}/chunk_"))
        
        # Sort chunks by number
        blobs.sort(key=lambda b: int(b.name.split("_")[-1]))
        
        # Use Compose to combine files in Cloud Storage
        if len(blobs) > 0:
            # For many chunks, we might need to do this in batches
            result_blob = self.bucket.blob(final_path)
            
            # Cloud Storage compose can only combine up to 32 blobs at once
            for i in range(0, len(blobs), 32):
                batch = blobs[i:i+32]
                
                if i == 0:  # First batch
                    if len(batch) > 1:
                        result_blob.compose(batch)
                    else:
                        # Just copy the single blob
                        self.bucket.copy_blob(batch[0], self.bucket, final_path)
                else:  # Subsequent batches
                    result_blob.compose([result_blob] + batch)
        
        # Update metadata
        metadata["status"] = "completed"
        metadata["final_path"] = final_path
        metadata["last_updated"] = str(self._get_timestamp())
        
        # Update metadata in storage
        metadata_blob = self.bucket.blob(f"{temp_folder}/metadata.json")
        metadata_blob.upload_from_string(
            json.dumps(metadata),
            content_type="application/json"
        )
        
        return metadata
    
    async def _get_upload_metadata(self, upload_id: str) -> Optional[Dict]:
        """Get metadata for an existing upload."""
        metadata_blob = self.bucket.blob(f"uploads/temp/{upload_id}/metadata.json")
        
        if not metadata_blob.exists():
            return None
            
        metadata_content = metadata_blob.download_as_text()
        return json.loads(metadata_content)
    
    def _get_timestamp(self):
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow()
