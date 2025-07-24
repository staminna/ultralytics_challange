# YOLO Dataset Management with CLI Tool

A comprehensive FastAPI-based service for managing YOLO datasets with integrated YOLO CLI tool support and MongoDB backend.

## 🚀 Quick Start

Get up and running in 3 simple steps:

```bash
# 1. Setup environment
conda env create -f environment.yml
conda activate dataset-annotation

# 2. Start services
docker-compose up -d  # MongoDB
python backend/server.py  # FastAPI server

# 3. Download and upload datasets
python scripts/download_datasets.py download coco8
python scripts/dynamic_dataset_uploader.py
```

## 📋 Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Environment Variables](#environment-variables)
- [MongoDB Management](#mongodb-management)
- [YOLO CLI Dataset Management](#yolo-cli-dataset-management)
- [Dataset Upload to Datastore](#dataset-upload-to-datastore)
- [Large Dataset Import](#large-dataset-import)
- [Model Deployment to GCS](#model-deployment-to-gcs)
- [Test Coverage and Unit Testing](#test-coverage-and-unit-testing)
- [API Usage](#api-usage)
- [Troubleshooting](#troubleshooting)

## ✨ Features

- **YOLO CLI Integration**: Official YOLO CLI tool for dataset downloads
- **MongoDB Backend**: Fast, scalable document storage with Beanie ODM
- **Dynamic Dataset Detection**: Automatically scans and uploads any YOLO dataset
- **Duplicate Prevention**: Smart duplicate detection with normalized name matching
- **Metadata Preservation**: Maintains YOLO structure (classes.txt, data.yaml)
- **Batch Processing**: Handles large datasets efficiently
- **RESTful API**: Complete CRUD operations with OpenAPI documentation

## 📋 Prerequisites

- **Python 3.12+**
- **Docker & Docker Compose** (for MongoDB)
- **Conda** (recommended for environment management)
- **YOLO CLI** (installed automatically with ultralytics package)

### Step 1: Create Conda Environment

```bash
# Create environment from file
conda env create -f environment.yml
conda activate dataset-annotation

# Or create manually
conda create -n dataset-annotation python=3.12
conda activate dataset-annotation
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env file with your settings (optional for development)
# The default values work for local development
```

### Step 3: Start Services

```bash
# Start MongoDB and mongo-express
docker-compose up -d mongo mongo-express

# Start FastAPI server
cd backend
python server.py
```

The server will be available at `http://localhost:8000` with API docs at `http://localhost:8000/docs`.

## ⚙️ Environment Variables

The project uses environment variables for configuration. Key variables include:

```bash
# Database Configuration
DATABASE_NAME=dataset_annotation          # MongoDB database name

# Mongo Express Web UI
ME_CONFIG_BASICAUTH_USERNAME=admin        # Web UI username
ME_CONFIG_BASICAUTH_PASSWORD=express      # Web UI password

# Google Cloud (Optional)
GCP_PROJECT_ID=your-gcp-project-id        # For cloud storage
GOOGLE_APPLICATION_CREDENTIALS=path/to/key # Service account key

# Development Settings
ENVIRONMENT=development                    # Environment mode
DEBUG=True                                # Debug mode
```

### Configuration Files

- **`.env`**: Your local environment variables (not committed to git)
- **`.env.example`**: Template with all available variables
- **`docker-compose.yml`**: Uses environment variables with `${VARIABLE_NAME}` syntax

### Security Notes

- ⚠️ **Never commit `.env` files** - they contain sensitive credentials
- ✅ **Use `.env.example`** as a template for new environments
- 🔒 **For production**: Use proper secrets management (Docker secrets, Kubernetes secrets, etc.)

## 🗄️ MongoDB Management

### MongoDB Express Web Interface

The project includes **mongo-express**, a web-based MongoDB admin interface for easy database inspection and management.

#### Access MongoDB Express

```bash
# After starting services with docker-compose up -d
# Open in your browser:
http://localhost:8081
```

#### Access Credentials

- **MongoDB**: No authentication required for development
- **Mongo Express Web UI**: 
  - Username: `admin` (configurable in `.env`)
  - Password: `express` (configurable in `.env`)
- **Database Name**: `dataset_annotation` (configurable in `.env`)

#### What You Can Do

- **📋 Browse Collections**: View datasets, images, and labels collections
- **🔍 Query Data**: Run MongoDB queries directly in the web interface
- **📊 View Statistics**: Check document counts and database size
- **🗑️ Delete Records**: Remove datasets or individual documents
- **📝 Edit Documents**: Modify dataset metadata and image annotations
- **📈 Monitor Performance**: View database operations and indexes

#### Useful Collections to Monitor

```
📁 Database: dataset_annotation
├── 📄 datasets          # Dataset metadata and configuration
├── 📄 images            # Image records with file paths and metadata  
├── 📄 labels            # YOLO annotation data and bounding boxes
└── 📄 class_definitions # Class names and IDs for each dataset
```

#### Example Queries

```javascript
// Find all datasets
db.datasets.find({})

// Count images in a specific dataset
db.images.countDocuments({"dataset_id": "your-dataset-id"})

// Find images without labels
db.images.find({"labels": {"$size": 0}})

// Get dataset statistics
db.datasets.aggregate([
  {
    $lookup: {
      from: "images",
      localField: "_id", 
      foreignField: "dataset_id",
      as: "images"
    }
  },
  {
    $project: {
      name: 1,
      image_count: {$size: "$images"},
      created_at: 1
    }
  }
])
```

#### Security Notes

- **Localhost Only**: All services bind to 127.0.0.1 (localhost) for security
- **Development Only**: mongo-express is configured for development use
- **Production**: Remove or secure mongo-express in production environments
- **Network Isolation**: Services only accessible from the host machine
- **Authentication**: Basic auth enabled for mongo-express web interface
- **Container Security**: Non-root user in backend container

## 📦 YOLO CLI Dataset Management

### Download Official YOLO Datasets

Use the integrated YOLO CLI tool to download official datasets:

```bash
# Import specific datasets

Endpoint: /api/v1/datasets/import/yolo

# Check dataset status
python scripts/download_datasets.py status

# Force re-download
python scripts/download_datasets.py download coco8 --force
```

### Available Datasets

| Dataset | Images | Classes | Size | Description |
|---------|--------|---------|------|--------------|
| `coco8` | 8 | 80 | ~6MB | Small COCO subset for testing |
| `coco128` | 128 | 80 | ~50MB | Medium COCO subset for development |
| `coco` | 118K | 80 | ~20GB | Full COCO dataset |
| `VOC` | 16K | 20 | ~4GB | Pascal VOC 2007+2012 |
| `Open Images v7` | 1.7M | 600 | ~500GB | Large-scale detection dataset |

### Dataset Structure Created

```
backend/datasets/
├── coco8/
│   ├── images/
│   │   ├── train/          # Training images
│   │   └── val/            # Validation images
│   ├── labels/
│   │   ├── train/          # Training labels (.txt)
│   │   └── val/            # Validation labels (.txt)
│   └── raw/
│       ├── coco8.yaml      # YOLO config file
│       └── classes.txt     # Class names
└── coco128/
    └── [same structure]
```

## 🚀 Dataset Upload to Datastore

### Automatic Upload (Recommended)

The dynamic dataset uploader automatically detects and uploads all datasets:

```bash
# Upload all datasets in backend/datasets/
python scripts/dynamic_dataset_uploader.py

# Upload specific dataset
python scripts/dynamic_dataset_uploader.py --dataset coco8

# Force upload (ignore duplicates)
python scripts/dynamic_dataset_uploader.py --force
```

### Manual Upload via API

```bash
# Import ZIP file
curl -X POST "http://localhost:8000/api/v1/datasets/import/yolo" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@dataset.zip" \
     -F "dataset_name=my_dataset"

# Check upload status
curl "http://localhost:8000/api/v1/datasets/{dataset_id}/import/status"
```

### Upload Features

- **🔍 Dynamic Detection**: Scans `backend/datasets/` for any YOLO dataset
- **🚫 Duplicate Prevention**: Compares normalized names to avoid duplicates
- **📁 Structure Preservation**: Maintains YOLO directory structure and metadata
- **📊 Progress Tracking**: Shows detailed upload progress and statistics
- **🔄 Batch Processing**: Handles multiple datasets efficiently

### Upload Output Example

```
🔍 Scanning for datasets in: /path/to/backend/datasets

📦 Found dataset: coco8
   📁 Structure: standard_yolo
   🖼️  Images: 8 (train: 4, val: 4)
   🏷️  Labels: 8 (train: 4, val: 4)
   📄 Metadata: classes.txt, coco8.yaml
   📊 Classes: 80 COCO classes

✅ Upload successful!
   📋 Dataset ID: 9d3e9d4d-73d9-4f90-abd8-c6d00d199c57
   ⏱️  Processing time: 2.3s
   💾 Total size: 6.2MB
```

## 📦 Large Dataset Import

### Chunked Upload for Large Files (>1GB)

For large datasets like COCO train2017 (18GB), use the chunked upload system:

```bash
# Import large dataset using chunked upload
python scripts/upload_coco_chunked.py
```

#### Features of Chunked Upload
- **Large File Support**: Handles files up to 100GB+
- **Resume Capability**: Can resume interrupted uploads
- **Progress Tracking**: Real-time progress with ETA
- **Integrity Checking**: SHA256 hash verification
- **Chunk Size**: Configurable (default: 10MB chunks)

#### Manual Chunked Upload Configuration

```python
# Configuration in upload_coco_chunked.py
COCO_FILE_PATH = "/path/to/your/large-dataset.zip"
CHUNK_SIZE = 10 * 1024 * 1024  # 10MB chunks
DATASET_NAME = "Your Large Dataset"
DATASET_DESCRIPTION = "Description of your dataset"
```

#### Upload Progress Example

```
🚀 COCO Dataset Chunked Upload
========================================
✅ Server is healthy and ready
📊 Calculating file hash for integrity checking...
✅ File hash: 69a8bb58ea5f8f99d24875f21416de2e9ded3178e903f1f7603e283b9e06d929
📋 Creating dataset metadata...
🚀 Starting chunked upload...
   File: coco-train2017-images.zip
   Size: 18.01 GB
   Chunk size: 10.0 MB
   Total chunks: 1845
📈 Progress: 17.7% (327/1845) - ETA: 2.9m
```

#### Alternative: Simple Import Script

For smaller files (<1GB), use the simple import script:

```bash
# Import smaller datasets
python scripts/import_dataset.py /path/to/dataset.zip "Dataset Name" --description="Description"
```

## ☁️ Model Deployment to GCS

### Prerequisites for GCS Deployment

1. **Google Cloud Project Setup**:
   ```bash
   # Install Google Cloud SDK
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   gcloud init
   ```

2. **Create Service Account**:
   ```bash
   # Create service account
   gcloud iam service-accounts create yolo-dataset-service \
       --description="YOLO Dataset Annotation Service" \
       --display-name="YOLO Dataset Service"
   
   # Grant necessary permissions
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
       --member="serviceAccount:yolo-dataset-service@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
       --role="roles/storage.admin"
   
   # Create and download key
   gcloud iam service-accounts keys create service-account-key.json \
       --iam-account=yolo-dataset-service@YOUR_PROJECT_ID.iam.gserviceaccount.com
   ```

### Environment Configuration for GCS

```bash
# Set environment variables
export GOOGLE_APPLICATION_CREDENTIALS="./service-account-key.json"
export GCP_PROJECT_ID="your-project-id"
export GCP_STORAGE_BUCKET="your-bucket-name"
```

### Model Upload to GCS

```python
# Example: Upload trained YOLO model to GCS
from backend.app.core.gcp import get_storage_bucket

def upload_model_to_gcs(local_model_path: str, gcs_model_path: str):
    """Upload YOLO model to Google Cloud Storage."""
    bucket = get_storage_bucket()
    blob = bucket.blob(gcs_model_path)
    
    with open(local_model_path, 'rb') as model_file:
        blob.upload_from_file(model_file)
    
    print(f"✅ Model uploaded to gs://{bucket.name}/{gcs_model_path}")
    return f"gs://{bucket.name}/{gcs_model_path}"

# Usage
upload_model_to_gcs(
    local_model_path="./models/yolo11n.pt",
    gcs_model_path="models/yolo11n-trained.pt"
)
```

### Automated Model Deployment Script

```bash
# Deploy model after training
python scripts/deploy_model_to_gcs.py \
    --model-path "./runs/train/exp/weights/best.pt" \
    --model-name "yolo11-custom-trained" \
    --version "v1.0"
```

### GCS Bucket Structure

```
your-bucket/
├── models/
│   ├── yolo11n.pt              # Base models
│   ├── yolo11s.pt
│   └── trained/
│       ├── custom-v1.0.pt      # Custom trained models
│       └── custom-v1.1.pt
├── datasets/
│   ├── raw/                    # Original datasets
│   └── processed/              # Processed datasets
└── exports/
    ├── onnx/                   # ONNX exports
    └── tensorrt/               # TensorRT exports
```

## 🧪 Test Coverage and Unit Testing

### Running All Tests

```bash
# Run all tests with coverage
pytest --cov=backend/app --cov-report=html --cov-report=term-missing

# Run specific test suite
pytest tests/test_final_coverage_push.py -v

# Run tests with detailed output
pytest tests/ -v --tb=short
```

### Test Coverage Reports

#### Generate HTML Coverage Report

```bash
# Generate comprehensive coverage report
pytest --cov=backend/app --cov-report=html --cov-report=term-missing

# Open coverage report in browser
open htmlcov/index.html
```

#### Current Coverage Status

```
Name                                                  Stmts   Miss  Cover   Missing
-----------------------------------------------------------------------------------
backend/app/core/config.py                              18      0   100%
backend/app/core/gcp.py                                 14      0   100%
backend/app/models/mongo_models.py                      45      0   100%
backend/app/schemas/dataset_schema.py                   77      0   100%
backend/app/schemas/dataset.py                          82      0   100%
backend/app/services/yolo_import_service.py             17      1    94%
backend/app/main.py                                     26      4    85%
backend/app/core/storage_paths.py                       58      9    84%
backend/app/api/routes/dataset_management_routes.py     31      6    81%
backend/app/api/routes/dataset_import_routes.py         33     10    70%
backend/app/services/yolo_validation_service.py        182     52    71%
backend/app/services/yolo_parsing_service.py           161     52    68%
backend/app/services/dataset_import_orchestrator.py    141     46    67%
backend/app/core/database.py                            32     14    56%
backend/app/core/storage.py                             96     45    53%
backend/app/services/chunked_upload_service.py         117     58    50%
-----------------------------------------------------------------------------------
TOTAL                                                 2158   1184    45%
```

### Test Suites Overview

#### 1. Comprehensive Coverage Tests
```bash
# Main coverage test suite (22 tests)
pytest tests/test_final_coverage_push.py
```

**Coverage Areas:**
- ✅ Chunked Upload Service (5 tests)
- ✅ Dataset Import Orchestrator (3 tests) 
- ✅ Storage Backend Testing (3 tests)
- ✅ Database Connection (2 tests)
- ✅ API Routes Coverage (4 tests)
- ✅ Service Methods (3 tests)
- ✅ Configuration & Paths (2 tests)

#### 2. API Integration Tests
```bash
# API endpoint tests
pytest tests/test_api.py tests/test_api_integration.py
```

#### 3. Service-Specific Tests
```bash
# Individual service tests
pytest tests/test_yolo_import.py
pytest tests/test_image_label_endpoints.py
pytest tests/test_main_api_endpoints.py
```

### Test Configuration

#### pytest.ini Configuration
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --disable-warnings
    --tb=short
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

#### Running Tests by Category

```bash
# Unit tests only
pytest -m unit

# Integration tests only  
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run with parallel execution
pytest -n auto  # Requires pytest-xdist
```

### Coverage Goals and Metrics

#### Current Status ✅ **MAJOR IMPROVEMENT ACHIEVED**
- **Overall Coverage**: 45% ⬆️ (was 29%, Target: 90%)
- **Core Modules**: 100% ✅ (config, gcp, models, schemas)
- **Services**: 50-94% ⬆️ (significant improvement)
- **API Routes**: 70-81% ⬆️ (major improvement)

#### Top Performing Modules
- **Models & Schemas**: 100% coverage across all files
- **YOLO Import Service**: 94% coverage
- **Main Application**: 85% coverage
- **Dataset Management Routes**: 81% coverage
- **Dataset Import Routes**: 70% coverage
- **YOLO Services**: 68-71% coverage

#### Coverage Improvement Plan
1. **Phase 1 ✅ COMPLETED**: Increased service coverage to 50-94%
2. **Phase 2**: Focus on 0% coverage modules (dataset_routes.py, mongodb_service.py, yolo_model_service.py)
3. **Phase 3**: Add integration tests for 90% total coverage

#### Test Quality Metrics
```bash
# Generate test quality report
pytest --cov=backend/app --cov-report=html --cov-branch

# Check for missing test coverage
pytest --cov=backend/app --cov-fail-under=30
```

### Continuous Integration

#### GitHub Actions Example
```yaml
name: Test Coverage
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests with coverage
        run: |
          pytest --cov=backend/app --cov-report=xml
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
```

## 🔌 API Usage

### Core Endpoints

```bash
# List all datasets
curl "http://localhost:8000/api/v1/datasets/"

# Get dataset details
curl "http://localhost:8000/api/v1/datasets/{dataset_id}"

# List images in dataset
curl "http://localhost:8000/api/v1/datasets/{dataset_id}/images"

# Delete dataset
curl -X DELETE "http://localhost:8000/api/v1/datasets/{dataset_id}"
```

### YOLO Dataset Import with curl

#### Basic YOLO Import

```bash
# Import YOLO dataset from ZIP file
curl -X POST "http://localhost:8000/api/v1/datasets/import/yolo" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@/path/to/your/dataset.zip" \
     -F "dataset_name=my_custom_dataset"
```

#### Advanced YOLO Import with Options

```bash
# Import with custom description and settings
curl -X POST "http://localhost:8000/api/v1/datasets/import/yolo" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@/path/to/coco8_dataset.zip" \
     -F "dataset_name=coco8_test" \
     -F "description=COCO 8-image subset for testing" \
     -v  # Verbose output for debugging
```

#### Example with Real Dataset

```bash
# First, create a test ZIP file from downloaded dataset
cd backend/datasets
zip -r coco8_test.zip coco8/

# Then import it via API
curl -X POST "http://localhost:8000/api/v1/datasets/import/yolo" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@coco8_test.zip" \
     -F "dataset_name=coco8_via_api" \
     -F "description=COCO8 dataset imported via REST API"
```

#### Expected Response

```json
{
  "message": "Dataset import started successfully",
  "dataset_id": "9d3e9d4d-73d9-4f90-abd8-c6d00d199c57",
  "status": "processing",
  "dataset_name": "coco8_via_api",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### Check Import Status

```bash
# Check the status of the import operation
curl "http://localhost:8000/api/v1/datasets/9d3e9d4d-73d9-4f90-abd8-c6d00d199c57/import/status"
```

#### Error Handling

```bash
# Import with error handling
curl -X POST "http://localhost:8000/api/v1/datasets/import/yolo" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@invalid_dataset.zip" \
     -F "dataset_name=test_error" \
     -w "\nHTTP Status: %{http_code}\n" \
     -s -S  # Silent but show errors
```

#### YOLO Dataset Requirements

Your ZIP file should contain:

```
dataset.zip
├── images/
│   ├── train/           # Training images (.jpg, .png)
│   └── val/             # Validation images
├── labels/
│   ├── train/           # Training labels (.txt)
│   └── val/             # Validation labels
├── classes.txt          # Class names (optional)
└── data.yaml           # YOLO config (optional)
```

#### Troubleshooting curl Commands

```bash
# Test server connectivity
curl -I "http://localhost:8000/api/v1/datasets/"

# Check file exists before upload
ls -la /path/to/your/dataset.zip

# Test with verbose output
curl -X POST "http://localhost:8000/api/v1/datasets/import/yolo" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@dataset.zip" \
     -F "dataset_name=test" \
     -v -L  # Verbose + follow redirects

# Check server logs if upload fails
docker-compose logs backend
```

### Response Examples

```json
// GET /api/v1/datasets/
{
  "datasets": [
    {
      "id": "9d3e9d4d-73d9-4f90-abd8-c6d00d199c57",
      "name": "coco8",
      "description": "COCO 8-image subset",
      "image_count": 8,
      "class_count": 80,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

## 🎯 Quick Setup Script

For immediate testing, use the automated setup:

```bash
# Download COCO8, upload to datastore, and validate
python scripts/quick_setup.py
```

This script:
1. Downloads COCO8 dataset (8 images)
2. Uploads to MongoDB datastore
3. Validates successful upload
4. Shows success metrics

## 🔧 Troubleshooting

### Common Issues

**MongoDB Connection Failed**
```bash
# Check if MongoDB and mongo-express are running
docker ps | grep mongo

# Restart all MongoDB services
docker-compose restart mongo mongo-express

# View MongoDB logs
docker-compose logs mongo

# Access mongo-express web interface
open http://localhost:8081
```

**YOLO CLI Download Fails**
```bash
# Update ultralytics
pip install --upgrade ultralytics

# Clear YOLO cache
yolo settings reset
```

**Dataset Upload Fails**
```bash
# Check server logs
tail -f backend/logs/app.log

# Verify dataset structure
python scripts/validate_dataset.py backend/datasets/coco8
```

**Duplicate Dataset Warnings**
```bash
# Clean up duplicates
python scripts/cleanup_duplicates.py

# Force fresh upload
python scripts/dynamic_dataset_uploader.py --force
```

### Performance Tips

- Use `coco8` for quick testing (8 images)
- Use `coco128` for development (128 images)
- Monitor disk space for large datasets
- Use `--force` flag sparingly to avoid unnecessary uploads

## 📊 Expected Results

After successful setup:
- **COCO8**: 8 images, 80 classes, ~6MB
- **COCO128**: 128 images, 80 classes, ~50MB
- **Total Processing**: ~264 images with 1,229+ detections
- **API Response Time**: <100ms for dataset listing
- **Upload Speed**: ~3MB/s for local datasets

## 🏗️ Architecture

### Technology Stack
- **Backend**: FastAPI with async/await
- **Database**: MongoDB with Beanie ODM
- **YOLO**: Official ultralytics CLI tool
- **Validation**: Pydantic v2 models
- **Documentation**: OpenAPI/Swagger UI

### Data Flow
1. **Download**: YOLO CLI downloads official datasets
2. **Scan**: Dynamic uploader detects datasets
3. **Process**: Images and labels are validated
4. **Store**: Metadata saved to MongoDB
5. **Serve**: RESTful API provides access

---

$ pytest --cov=backend/app tests/

---

## 📝 Development Notes

- All datasets stored in `backend/datasets/`
- MongoDB runs on `127.0.0.1:27017` (localhost only)
- MongoDB Express web UI on `127.0.0.1:8081` (localhost only)
- API server runs on `127.0.0.1:8000` (localhost only)
- All services secured with localhost-only binding
- Backend container runs as non-root user
- Logs available in `backend/logs/`
- Use pip for dependency management (Docker) or conda (local)

For issues or contributions, check the project repository.