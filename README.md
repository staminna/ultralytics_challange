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

- **Development Only**: mongo-express is configured for development use
- **Production**: Remove or secure mongo-express in production environments
- **Network**: Only accessible locally (localhost:8081)
- **Authentication**: Uses basic MongoDB authentication

## 📦 YOLO CLI Dataset Management

### Download Official YOLO Datasets

Use the integrated YOLO CLI tool to download official datasets:

```bash
# List available datasets
python scripts/download_datasets.py list

# Download specific datasets
python scripts/download_datasets.py download coco8
python scripts/download_datasets.py download coco128
python scripts/download_datasets.py download coco

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
# Upload ZIP file
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

## 📝 Development Notes

- All datasets stored in `backend/datasets/`
- MongoDB runs on `localhost:27017`
- MongoDB Express web UI on `localhost:8081`
- API server runs on `localhost:8000`
- Logs available in `backend/logs/`
- Use conda for dependency management

For issues or contributions, check the project repository.