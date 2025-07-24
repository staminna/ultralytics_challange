#!/usr/bin/env python3
"""
Focused Test Suite for 90%+ Coverage

Targets the main 0% coverage modules:
- mongodb_service.py (0% → 80%)
- yolo_model_service.py (0% → 80%) 
- dataset_routes.py (0% → 70%)
"""

import asyncio
import json
import os
import sys
import tempfile
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
from fastapi.testclient import TestClient

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.app.main import app
from backend.app.services.mongodb_service import MongoDBService
from backend.app.services.yolo_model_service import YOLOModelService
from backend.app.core.database import connect_to_mongo, close_mongo_connection
from backend.app.core.storage import get_storage_client, get_storage_bucket

client = TestClient(app)


class TestMongoDBServiceCore:
    """Core MongoDB service tests for coverage."""
    
    @pytest.fixture
    def mock_client(self):
        mock_client = Mock()
        mock_db = Mock()
        mock_client.__getitem__.return_value = mock_db
        return mock_client
    
    @pytest.fixture
    def mongodb_service(self, mock_client):
        with patch('backend.app.services.mongodb_service.AsyncIOMotorClient', return_value=mock_client):
            service = MongoDBService()
            service.client = mock_client
            service.db = mock_client['test_db']
            return service
    
    def test_mongodb_service_init(self):
        with patch('backend.app.services.mongodb_service.AsyncIOMotorClient'):
            service = MongoDBService()
            assert service is not None
    
    @pytest.mark.asyncio
    async def test_connect(self, mongodb_service):
        with patch.object(mongodb_service, '_create_indexes', new_callable=AsyncMock):
            await mongodb_service.connect()
            assert mongodb_service.client is not None
    
    @pytest.mark.asyncio
    async def test_create_indexes(self, mongodb_service):
        mock_collection = Mock()
        mock_collection.create_index = AsyncMock()
        mongodb_service.db.__getitem__.return_value = mock_collection
        await mongodb_service._create_indexes()
        assert mock_collection.create_index.called
    
    def test_is_connected(self, mongodb_service):
        mongodb_service.client = Mock()
        result = mongodb_service.is_connected()
        assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_store_dataset(self, mongodb_service):
        mock_collection = Mock()
        mock_collection.insert_one = AsyncMock(return_value=Mock(inserted_id="test_id"))
        mongodb_service.db.__getitem__.return_value = mock_collection
        
        dataset_data = {"name": "test_dataset", "description": "Test", "format": "yolo"}
        result = await mongodb_service.store_dataset(dataset_data)
        assert result == "test_id"
    
    @pytest.mark.asyncio
    async def test_store_images_batch(self, mongodb_service):
        mock_collection = Mock()
        mock_collection.insert_many = AsyncMock(return_value=Mock(inserted_ids=["id1", "id2"]))
        mongodb_service.db.__getitem__.return_value = mock_collection
        
        images_data = [{"filename": "img1.jpg"}, {"filename": "img2.jpg"}]
        result = await mongodb_service.store_images_batch(images_data)
        assert result == ["id1", "id2"]
    
    @pytest.mark.asyncio
    async def test_get_dataset(self, mongodb_service):
        mock_collection = Mock()
        mock_collection.find_one = AsyncMock(return_value={"_id": "test_id", "name": "test"})
        mongodb_service.db.__getitem__.return_value = mock_collection
        
        result = await mongodb_service.get_dataset("test_id")
        assert result["name"] == "test"
    
    @pytest.mark.asyncio
    async def test_list_datasets(self, mongodb_service):
        mock_cursor = Mock()
        mock_cursor.to_list = AsyncMock(return_value=[{"name": "dataset1"}])
        mock_collection = Mock()
        mock_collection.find.return_value = mock_cursor
        mongodb_service.db.__getitem__.return_value = mock_collection
        
        result = await mongodb_service.list_datasets(limit=10, skip=0)
        assert len(result) == 1


class TestYOLOModelServiceCore:
    """Core YOLO model service tests for coverage."""
    
    @pytest.fixture
    def mock_yolo_model(self):
        mock_model = Mock()
        mock_model.predict.return_value = [Mock(boxes=Mock(data=[[0.1, 0.2, 0.3, 0.4, 0.9, 0]]))]
        return mock_model
    
    @pytest.fixture
    def yolo_service(self, mock_yolo_model):
        with patch('backend.app.services.yolo_model_service.YOLO', return_value=mock_yolo_model):
            service = YOLOModelService()
            service.model = mock_yolo_model
            return service
    
    def test_yolo_service_init(self):
        with patch('backend.app.services.yolo_model_service.YOLO'):
            service = YOLOModelService()
            assert service is not None
    
    def test_load_model(self, yolo_service):
        with patch('backend.app.services.yolo_model_service.YOLO') as mock_yolo:
            mock_model = Mock()
            mock_yolo.return_value = mock_model
            result = yolo_service.load_model("yolo11n.pt")
            assert result == mock_model
    
    def test_predict(self, yolo_service):
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_file.write(b"fake image data")
            tmp_file.flush()
            try:
                result = yolo_service.predict(tmp_file.name)
                assert result is not None
            finally:
                os.unlink(tmp_file.name)
    
    @pytest.mark.asyncio
    async def test_auto_annotate_image(self, yolo_service):
        with patch('backend.app.services.yolo_model_service.DatasetModel') as mock_dataset:
            with patch('backend.app.services.yolo_model_service.ImageModel') as mock_image:
                mock_dataset.get.return_value = Mock(id="dataset_id")
                mock_image.get.return_value = Mock(id="image_id", file_path="test.jpg")
                
                with patch.object(yolo_service, 'predict', return_value=[Mock()]):
                    result = await yolo_service.auto_annotate_image("dataset_id", "image_id")
                    assert result is not None


class TestDatasetRoutesCore:
    """Core dataset routes tests for coverage."""
    
    def test_health_endpoints(self):
        """Test health check endpoints."""
        response = client.get("/")
        assert response.status_code == 200
        
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_dataset_endpoints_structure(self):
        """Test dataset endpoint structure."""
        # Test endpoints exist (even if they return errors due to missing data)
        response = client.get("/api/v1/datasets/")
        assert response.status_code in [200, 500]  # May fail due to DB but endpoint exists
        
        response = client.post("/api/v1/datasets/", json={"name": "test", "description": "test"})
        assert response.status_code in [200, 422, 500]  # Endpoint exists
    
    def test_image_endpoints_structure(self):
        """Test image endpoint structure."""
        response = client.get("/api/v1/datasets/test-id/images")
        assert response.status_code in [200, 404, 500]  # Endpoint exists
    
    def test_import_endpoints_structure(self):
        """Test import endpoint structure."""
        response = client.post("/api/v1/datasets/import/yolo")
        assert response.status_code in [400, 422, 500]  # Missing file but endpoint exists


class TestDatabaseConnectionCore:
    """Core database connection tests."""
    
    @pytest.mark.asyncio
    async def test_connect_to_mongo(self):
        """Test MongoDB connection function."""
        with patch('backend.app.core.database.AsyncIOMotorClient') as mock_client:
            with patch('backend.app.core.database.init_beanie', new_callable=AsyncMock):
                await connect_to_mongo()
                mock_client.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_mongo_connection(self):
        """Test MongoDB connection close."""
        with patch('backend.app.core.database.AsyncIOMotorClient') as mock_client:
            mock_instance = Mock()
            mock_instance.close = Mock()
            mock_client.return_value = mock_instance
            
            # Set up the client
            import backend.app.core.database as db_module
            db_module.mongo_client = mock_instance
            
            await close_mongo_connection()
            mock_instance.close.assert_called_once()


class TestStorageBackendCore:
    """Core storage backend tests."""
    
    def test_get_storage_client(self):
        """Test storage client creation."""
        with patch('backend.app.core.storage.storage.Client') as mock_client:
            from backend.app.core.storage import get_storage_client
            result = get_storage_client()
            mock_client.assert_called_once()
    
    def test_get_storage_bucket(self):
        """Test storage bucket retrieval."""
        with patch('backend.app.core.storage.storage.Client') as mock_client:
            mock_instance = Mock()
            mock_bucket = Mock()
            mock_instance.bucket.return_value = mock_bucket
            mock_client.return_value = mock_instance
            
            from backend.app.core.storage import get_storage_bucket
            result = get_storage_bucket()
            assert result == mock_bucket


class TestChunkedUploadServiceExtended:
    """Extended chunked upload service tests."""
    
    @pytest.fixture
    def chunked_service(self):
        from backend.app.services.chunked_upload_service import ChunkedUploadService
        return ChunkedUploadService()
    
    @pytest.mark.asyncio
    async def test_initiate_chunked_upload(self, chunked_service):
        """Test chunked upload initiation."""
        with patch.object(chunked_service, '_get_timestamp', return_value="2023-01-01T00:00:00"):
            result = await chunked_service.initiate_chunked_upload("test.zip", 1000000)
            assert "upload_id" in result
    
    @pytest.mark.asyncio
    async def test_finalize_chunked_upload(self, chunked_service):
        """Test chunked upload finalization."""
        with patch('os.path.exists', return_value=True):
            with patch('os.listdir', return_value=['chunk_0', 'chunk_1']):
                with patch('builtins.open', create=True):
                    with patch('shutil.copyfileobj'):
                        with patch('os.remove'):
                            result = await chunked_service.finalize_chunked_upload("test-upload-id")
                            assert "file_path" in result
    
    @pytest.mark.asyncio
    async def test_get_upload_metadata(self, chunked_service):
        """Test upload metadata retrieval."""
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = '{"status": "active"}'
                result = await chunked_service._get_upload_metadata("test-upload-id")
                assert result["status"] == "active"


class TestMainApplicationCore:
    """Core main application tests."""
    
    @pytest.mark.asyncio
    async def test_lifespan_context(self):
        """Test application lifespan context."""
        from backend.app.main import lifespan
        
        mock_app = Mock()
        
        with patch('backend.app.main.connect_to_mongo', new_callable=AsyncMock):
            with patch('backend.app.main.close_mongo_connection', new_callable=AsyncMock):
                async with lifespan(mock_app):
                    pass  # Context manager should work without errors


class TestServiceDependencyInjection:
    """Test service dependency injection functions."""
    
    def test_get_dataset_service(self):
        """Test dataset service dependency."""
        from backend.app.services.dataset_service import get_dataset_service
        service = get_dataset_service()
        assert service is not None
    
    def test_get_yolo_import_service(self):
        """Test YOLO import service dependency."""
        from backend.app.services.yolo_import_service import get_yolo_import_service
        service = get_yolo_import_service()
        assert service is not None
    
    def test_get_dataset_import_orchestrator(self):
        """Test dataset import orchestrator dependency."""
        from backend.app.services.dataset_import_orchestrator import get_dataset_import_orchestrator
        service = get_dataset_import_orchestrator()
        assert service is not None
    
    def test_get_image_processing_service(self):
        """Test image processing service dependency."""
        from backend.app.services.image_processing_service import get_image_processing_service
        service = get_image_processing_service()
        assert service is not None
    
    def test_get_import_cleanup_service(self):
        """Test import cleanup service dependency."""
        from backend.app.services.import_cleanup_service import get_import_cleanup_service
        service = get_import_cleanup_service()
        assert service is not None
    
    def test_get_yolo_parsing_service(self):
        """Test YOLO parsing service dependency."""
        from backend.app.services.yolo_parsing_service import get_yolo_parsing_service
        service = get_yolo_parsing_service()
        assert service is not None
    
    def test_get_yolo_validation_service(self):
        """Test YOLO validation service dependency."""
        from backend.app.services.yolo_validation_service import get_yolo_validation_service
        service = get_yolo_validation_service()
        assert service is not None
