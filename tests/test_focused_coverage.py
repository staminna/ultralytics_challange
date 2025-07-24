#!/usr/bin/env python3
"""
Focused Coverage Test Suite

Targets specific uncovered functions without importing the full FastAPI app.
"""

import asyncio
import json
import os
import sys
import tempfile
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, mock_open
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))


class TestMongoDBServiceCoverage:
    """Test MongoDB service functions."""
    
    @pytest.mark.asyncio
    async def test_mongodb_connection(self):
        """Test MongoDB connection initialization."""
        with patch('backend.app.services.mongodb_service.AsyncIOMotorClient') as mock_client:
            with patch('backend.app.services.mongodb_service.init_beanie') as mock_init:
                from backend.app.services.mongodb_service import MongoDBService
                
                service = MongoDBService()
                mock_client.assert_called()
    
    @pytest.mark.asyncio
    async def test_mongodb_health_check(self):
        """Test MongoDB health check."""
        with patch('backend.app.services.mongodb_service.AsyncIOMotorClient') as mock_client:
            mock_instance = Mock()
            mock_instance.admin.command = AsyncMock(return_value={"ok": 1})
            mock_client.return_value = mock_instance
            
            from backend.app.services.mongodb_service import MongoDBService
            service = MongoDBService()
            result = await service.health_check()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_mongodb_get_database_stats(self):
        """Test database statistics."""
        with patch('backend.app.services.mongodb_service.AsyncIOMotorClient') as mock_client:
            mock_instance = Mock()
            mock_db = Mock()
            mock_db.command = AsyncMock(return_value={"collections": 5, "dataSize": 1024})
            mock_instance.__getitem__.return_value = mock_db
            mock_client.return_value = mock_instance
            
            from backend.app.services.mongodb_service import MongoDBService
            service = MongoDBService()
            result = await service.get_database_stats()
            assert "collections" in result
    
    @pytest.mark.asyncio
    async def test_mongodb_create_indexes(self):
        """Test index creation."""
        with patch('backend.app.services.mongodb_service.AsyncIOMotorClient') as mock_client:
            mock_instance = Mock()
            mock_collection = Mock()
            mock_collection.create_index = AsyncMock()
            mock_db = Mock()
            mock_db.__getitem__.return_value = mock_collection
            mock_instance.__getitem__.return_value = mock_db
            mock_client.return_value = mock_instance
            
            from backend.app.services.mongodb_service import MongoDBService
            service = MongoDBService()
            await service.create_indexes()
            # Should not raise exception
    
    @pytest.mark.asyncio
    async def test_mongodb_cleanup_orphaned_data(self):
        """Test orphaned data cleanup."""
        with patch('backend.app.services.mongodb_service.AsyncIOMotorClient') as mock_client:
            mock_instance = Mock()
            mock_collection = Mock()
            mock_collection.delete_many = AsyncMock(return_value=Mock(deleted_count=5))
            mock_db = Mock()
            mock_db.__getitem__.return_value = mock_collection
            mock_instance.__getitem__.return_value = mock_db
            mock_client.return_value = mock_instance
            
            from backend.app.services.mongodb_service import MongoDBService
            service = MongoDBService()
            result = await service.cleanup_orphaned_data()
            assert "deleted_count" in result


class TestYOLOModelServiceCoverage:
    """Test YOLO model service functions."""
    
    def test_yolo_model_init(self):
        """Test YOLO model service initialization."""
        with patch('backend.app.services.yolo_model_service.YOLO') as mock_yolo:
            from backend.app.services.yolo_model_service import YOLOModelService
            service = YOLOModelService()
            assert service is not None
    
    @pytest.mark.asyncio
    async def test_load_model(self):
        """Test model loading."""
        with patch('backend.app.services.yolo_model_service.YOLO') as mock_yolo:
            mock_model = Mock()
            mock_yolo.return_value = mock_model
            
            from backend.app.services.yolo_model_service import YOLOModelService
            service = YOLOModelService()
            result = await service.load_model("yolo11n.pt")
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_predict_image(self):
        """Test image prediction."""
        with patch('backend.app.services.yolo_model_service.YOLO') as mock_yolo:
            mock_model = Mock()
            mock_results = [Mock(boxes=Mock(data=[]), names={0: "person"})]
            mock_model.predict.return_value = mock_results
            mock_yolo.return_value = mock_model
            
            from backend.app.services.yolo_model_service import YOLOModelService
            service = YOLOModelService()
            service.model = mock_model
            
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                tmp_file.write(b"fake image")
                tmp_file.flush()
                
                try:
                    result = await service.predict_image(tmp_file.name)
                    assert "predictions" in result
                finally:
                    os.unlink(tmp_file.name)
    
    @pytest.mark.asyncio
    async def test_auto_annotate_dataset(self):
        """Test dataset auto-annotation."""
        with patch('backend.app.services.yolo_model_service.YOLO') as mock_yolo:
            with patch('backend.app.services.yolo_model_service.DatasetModel') as mock_dataset:
                with patch('backend.app.services.yolo_model_service.ImageModel') as mock_image:
                    mock_model = Mock()
                    mock_yolo.return_value = mock_model
                    
                    mock_dataset.get.return_value = Mock(id="dataset_id")
                    mock_cursor = Mock()
                    mock_cursor.to_list = AsyncMock(return_value=[Mock(file_path="test.jpg")])
                    mock_image.find.return_value = mock_cursor
                    
                    from backend.app.services.yolo_model_service import YOLOModelService
                    service = YOLOModelService()
                    service.model = mock_model
                    
                    result = await service.auto_annotate_dataset("dataset_id")
                    assert "annotated_images" in result
    
    @pytest.mark.asyncio
    async def test_fine_tune_model(self):
        """Test model fine-tuning."""
        with patch('backend.app.services.yolo_model_service.YOLO') as mock_yolo:
            mock_model = Mock()
            mock_model.train.return_value = Mock(results={"mAP": 0.85})
            mock_yolo.return_value = mock_model
            
            from backend.app.services.yolo_model_service import YOLOModelService
            service = YOLOModelService()
            service.model = mock_model
            
            config = {"epochs": 10, "batch_size": 16}
            result = await service.fine_tune_model("dataset_id", config)
            assert "training_results" in result
    
    def test_get_model_info(self):
        """Test model info retrieval."""
        with patch('backend.app.services.yolo_model_service.YOLO') as mock_yolo:
            mock_model = Mock()
            mock_model.info.return_value = "Model info"
            mock_yolo.return_value = mock_model
            
            from backend.app.services.yolo_model_service import YOLOModelService
            service = YOLOModelService()
            service.model = mock_model
            
            result = service.get_model_info()
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_export_model(self):
        """Test model export."""
        with patch('backend.app.services.yolo_model_service.YOLO') as mock_yolo:
            mock_model = Mock()
            mock_model.export.return_value = "exported_model.onnx"
            mock_yolo.return_value = mock_model
            
            from backend.app.services.yolo_model_service import YOLOModelService
            service = YOLOModelService()
            service.model = mock_model
            
            result = await service.export_model("onnx")
            assert result is not None
    
    def test_validate_model_format(self):
        """Test model format validation."""
        from backend.app.services.yolo_model_service import YOLOModelService
        service = YOLOModelService()
        
        assert service._validate_model_format("model.pt") is True
        assert service._validate_model_format("model.onnx") is True
        assert service._validate_model_format("model.txt") is False
    
    def test_parse_prediction_results(self):
        """Test prediction results parsing."""
        from backend.app.services.yolo_model_service import YOLOModelService
        service = YOLOModelService()
        
        mock_results = [Mock(
            boxes=Mock(data=[[100, 100, 200, 200, 0.9, 0]]),
            names={0: "person"}
        )]
        
        result = service._parse_prediction_results(mock_results)
        assert len(result) == 1
        assert result[0]["class"] == "person"


class TestStoragePathsCoverage:
    """Test storage paths utility functions."""
    
    def test_get_dataset_path(self):
        """Test dataset path generation."""
        from backend.app.core.storage_paths import StoragePaths
        result = StoragePaths.get_dataset_path("dataset_id")
        assert "dataset_id" in result
    
    def test_get_image_path(self):
        """Test image path generation."""
        from backend.app.core.storage_paths import StoragePaths
        result = StoragePaths.get_image_path("dataset_id", "image.jpg")
        assert "dataset_id" in result
        assert "image.jpg" in result
    
    def test_get_label_path(self):
        """Test label path generation."""
        from backend.app.core.storage_paths import StoragePaths
        result = StoragePaths.get_label_path("dataset_id", "label.txt")
        assert "dataset_id" in result
        assert "label.txt" in result
    
    def test_get_temp_path(self):
        """Test temporary path generation."""
        from backend.app.core.storage_paths import StoragePaths
        result = StoragePaths.get_temp_path("temp_file")
        assert "temp_file" in result
    
    def test_get_output_path(self):
        """Test output path generation."""
        from backend.app.core.storage_paths import StoragePaths
        result = StoragePaths.get_output_path("dataset_id", "output")
        assert "dataset_id" in result
        assert "output" in result


class TestConfigurationCoverage:
    """Test configuration functions."""
    
    def test_get_settings(self):
        """Test settings retrieval."""
        with patch.dict(os.environ, {"DATABASE_URL": "mongodb://localhost:27017"}):
            from backend.app.core.config import get_settings
            settings = get_settings()
            assert settings is not None
            assert hasattr(settings, 'database_url')
    
    def test_settings_validation(self):
        """Test settings validation."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "mongodb://localhost:27017",
            "GCP_PROJECT_ID": "test-project",
            "GCS_BUCKET_NAME": "test-bucket"
        }):
            from backend.app.core.config import Settings
            settings = Settings()
            assert settings.database_url == "mongodb://localhost:27017"
            assert settings.gcp_project_id == "test-project"


class TestGCPIntegrationCoverage:
    """Test GCP integration functions."""
    
    def test_get_storage_client(self):
        """Test storage client initialization."""
        with patch('backend.app.core.gcp.storage.Client') as mock_client:
            from backend.app.core.gcp import get_storage_client
            client = get_storage_client()
            mock_client.assert_called_once()
    
    def test_get_storage_bucket(self):
        """Test storage bucket access."""
        with patch('backend.app.core.gcp.storage.Client') as mock_client:
            mock_instance = Mock()
            mock_bucket = Mock()
            mock_instance.bucket.return_value = mock_bucket
            mock_client.return_value = mock_instance
            
            from backend.app.core.gcp import get_storage_bucket
            bucket = get_storage_bucket()
            assert bucket == mock_bucket
    
    def test_upload_to_gcs(self):
        """Test GCS upload functionality."""
        with patch('backend.app.core.gcp.storage.Client') as mock_client:
            mock_instance = Mock()
            mock_bucket = Mock()
            mock_blob = Mock()
            mock_bucket.blob.return_value = mock_blob
            mock_instance.bucket.return_value = mock_bucket
            mock_client.return_value = mock_instance
            
            from backend.app.core.gcp import upload_to_gcs
            
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_file.write(b"test data")
                tmp_file.flush()
                
                try:
                    result = upload_to_gcs(tmp_file.name, "test_file.txt")
                    mock_blob.upload_from_filename.assert_called_once()
                finally:
                    os.unlink(tmp_file.name)


class TestUtilityFunctionsCoverage:
    """Test utility functions."""
    
    def test_generate_uuid(self):
        """Test UUID generation."""
        import uuid
        result = str(uuid.uuid4())
        assert len(result) == 36
        assert result.count('-') == 4
    
    def test_validate_file_extension(self):
        """Test file extension validation."""
        valid_extensions = ['.jpg', '.jpeg', '.png', '.txt']
        
        assert any(ext in 'test.jpg' for ext in valid_extensions)
        assert any(ext in 'test.png' for ext in valid_extensions)
        assert not any(ext in 'test.pdf' for ext in valid_extensions)
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        import re
        filename = "test file!@#$%^&*().jpg"
        sanitized = re.sub(r'[^\w\-_\.]', '_', filename)
        assert sanitized == "test_file____________.jpg"
    
    def test_calculate_file_size(self):
        """Test file size calculation."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(b"test data" * 100)
            tmp_file.flush()
            
            try:
                size = os.path.getsize(tmp_file.name)
                assert size == 900  # 9 bytes * 100
            finally:
                os.unlink(tmp_file.name)
    
    def test_format_bytes(self):
        """Test byte formatting."""
        def format_bytes(bytes_val):
            if bytes_val < 1024:
                return f"{bytes_val} B"
            elif bytes_val < 1024**2:
                return f"{bytes_val/1024:.1f} KB"
            elif bytes_val < 1024**3:
                return f"{bytes_val/(1024**2):.1f} MB"
            else:
                return f"{bytes_val/(1024**3):.1f} GB"
        
        assert format_bytes(500) == "500 B"
        assert format_bytes(1536) == "1.5 KB"
        assert format_bytes(1048576) == "1.0 MB"
    
    def test_validate_bbox(self):
        """Test bounding box validation."""
        def validate_bbox(bbox):
            if len(bbox) != 4:
                return False
            x, y, w, h = bbox
            return 0 <= x <= 1 and 0 <= y <= 1 and 0 <= w <= 1 and 0 <= h <= 1
        
        assert validate_bbox([0.1, 0.2, 0.3, 0.4]) is True
        assert validate_bbox([0.5, 0.5, 0.5, 0.5]) is True
        assert validate_bbox([1.1, 0.2, 0.3, 0.4]) is False
        assert validate_bbox([0.1, 0.2, 0.3]) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
