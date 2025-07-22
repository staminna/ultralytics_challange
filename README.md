# Dataset Annotation Service - YOLO Format

This repository contains a SaaS product for dataset annotation, focusing specifically on importing and managing datasets in YOLO format for computer vision tasks.

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.12+
- Google Cloud Platform account with Firestore and Cloud Storage enabled
- Service account key (`service-account-key.json`) in the project root

### Step 1: Environment Setup
```bash
# Create and activate conda environment
conda create -n dataset-annotation python=3.9
conda activate dataset-annotation

# Install dependencies
cd backend
pip install -r requirements.txt
```

### Step 2: Start the Backend Server
```bash
# From the backend directory
python server.py
# or
uvicorn app.main:app --reload

# Server will be available at: http://localhost:8000
# API docs at: http://localhost:8000/docs
```

### Step 3: Test YOLO Dataset Import

#### Option A: Test with Existing Dataset (10 labeled images)
```bash
# From project root
python test_import_step_by_step.py
```

#### Option B: Upload Additional Raw Images (46 images)
```bash
python upload_additional_images.py
```

#### Option C: Create Complete Dataset (56 total images)
```bash
# Combines labeled + unlabeled images
python setup_complete_yolo_dataset.py
# Then upload the generated ZIP via API or test script
```

### Step 4: Verify Import Success

1. **Check Server Logs**: Look for successful image/label processing
2. **API Response**: Should return dataset ID and metadata
3. **Cloud Storage**: Images stored under `datasets/{dataset-id}/images/`
4. **Firestore**: Dataset metadata, images, and labels collections populated

## Core Features Implemented

1. **Import datasets in YOLO format**: Upload ZIP archives containing images and YOLO-format annotations
2. **List datasets**: Browse and manage your dataset collection with pagination
3. **List images with labels for a dataset**: View all images with their bounding box annotations
4. **Chunked uploads**: Support for large datasets up to 100GB
5. **Background processing**: Async import for better performance

## Architecture & Technical Approach

This solution is built as a cloud-native application leveraging Google Cloud Platform (GCP) services:

- **FastAPI Backend**: Modern, high-performance Python web framework with automatic OpenAPI documentation
- **Cloud Firestore**: NoSQL document database for storing dataset, image, and label metadata
- **Cloud Storage**: Object storage for raw image files and dataset archives
- **Cloud Run**: Serverless deployment platform for the API service

## 📋 API Endpoints

### Dataset Management
- `POST /api/v1/datasets/` - Create a new dataset
- `GET /api/v1/datasets/` - List all datasets (with pagination)
- `GET /api/v1/datasets/{dataset_id}` - Get specific dataset details
- `GET /api/v1/datasets/{dataset_id}/images` - List images with labels for a dataset

### YOLO Import
- `POST /api/v1/datasets/import/yolo` - Import YOLO dataset from ZIP file
- `POST /api/v1/datasets/import/yolo/chunk` - Chunked upload for large datasets
- `GET /api/v1/datasets/{dataset_id}/import/status` - Check import progress

### Image Management
- `POST /api/v1/datasets/{dataset_id}/images` - Upload single image to dataset
- `POST /api/v1/datasets/{dataset_id}/images/{image_id}/labels` - Add label to image

### Interactive API Documentation
Visit `http://localhost:8000/docs` for full Swagger/OpenAPI documentation with interactive testing.

## 🔧 Troubleshooting

### Common Issues

#### 1. Import Returns 200 but No Images Processed
**Symptoms**: API returns success but dataset shows 0 images
**Solutions**:
- Restart the backend server: `python server.py`
- Check server logs for specific errors
- Verify YOLO dataset structure: `images/train/` and `labels/train/`

#### 2. Label Processing Errors
**Symptoms**: Images upload but labels fail with attribute errors
**Solutions**:
- Ensure YOLO label files have correct format: `class_id x_center y_center width height`
- Verify coordinates are normalized (0-1 range)
- Check that class IDs exist in dataset

#### 3. File Upload Errors
**Symptoms**: 422 Unprocessable Entity on file upload
**Solutions**:
- Use correct form field name: `image` (not `file`)
- Ensure file is valid image format (JPG, PNG)
- Check file size limits

#### 4. GCP Authentication Issues
**Symptoms**: 403 Forbidden or authentication errors
**Solutions**:
- Verify `service-account-key.json` exists in project root
- Check GCP service account has Firestore and Storage permissions
- Ensure GCP project ID is correctly configured

### Dataset Storage Structure

Datasets are stored using **dataset IDs** (not names) for backend consistency:

```
Cloud Storage:
└── yolo_datasets_ultralytics/
    └── datasets/
        └── {dataset-id}/          # e.g., fadb65eb-4d88-45a1-ac18-2815ebe7a060
            ├── images/
            │   └── train/
            └── extracted/          # Original ZIP contents
                ├── images/
                └── labels/

Firestore Collections:
├── datasets                       # Dataset metadata
├── images                        # Image records
└── labels                        # Label/annotation records
```

## Project Structure

```
/backend
  /app
    /api
      /routes         # API endpoints
    /core            # Core configurations
    /models          # Data models
    /schemas         # Pydantic schemas for validation
    /services        # Business logic
  /tests            # Unit and integration tests
/scripts             # Helper scripts for testing and setup
```

## Design Decisions & Trade-offs

### Why Firestore over SQL?

I chose Firestore (NoSQL) over a traditional SQL database for several reasons:

1. **Schema Flexibility**: Annotation data models may evolve over time as we add features
2. **Horizontal Scaling**: Firestore automatically scales with increased load without manual sharding
3. **GCP Integration**: Seamless integration with other GCP services
4. **Nested Data**: Natural representation of hierarchical data (datasets → images → labels)

### API Design Choices

1. **Pagination**: All listing endpoints support pagination to handle large datasets efficiently
2. **File Upload Handling**: Streaming file uploads directly to Cloud Storage for efficient processing
3. **YOLO Format Support**: Specialized parser for the industry-standard YOLO annotation format

### Performance Considerations

1. **Signed URLs**: Pre-signed URLs for image access, avoiding proxy downloads through the API
2. **Batch Operations**: Where possible, using batch operations for Firestore to reduce network overhead
3. **Lazy Loading**: Images and labels are loaded only when requested, not with the dataset list

### Security Considerations

1. **GCP IAM**: Leveraging GCP's Identity and Access Management for service security
2. **Input Validation**: Comprehensive validation of all API inputs using Pydantic
3. **Isolated Storage**: Dataset data isolation within Cloud Storage

## Future Enhancements

1. Add authentication and user management
2. Implement frontend UI for dataset visualization and management
3. Add support for other annotation formats beyond YOLO
4. Implement annotation editing capabilities
5. Add export functionality to different formats

## GCP Setup

Create a billing account and a project.

Create a service account and grant it the necessary permissions.

On the gcloud shell run:
```bash
gcloud services enable run.googleapis.com \
  storage.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com
```

## Environment Setup

This project supports both conda and pyenv for environment management. Choose the option that fits your workflow best.

### Option 1: Using Conda

```bash
# Create and activate the conda environment
conda env create -f environment.yml
conda activate dataset-annotation

# Set up your GCP credentials
export GOOGLE_APPLICATION_CREDENTIALS="service-account-key.json"
```

### Option 2: Using Pyenv with Virtualenv

```bash
# Install the Python version specified in .python-version
pyenv install --skip-existing $(cat .python-version)

# Create and activate a virtual environment
pyenv virtualenv $(cat .python-version) dataset-annotation
pyenv local dataset-annotation

# Install dependencies
pip install -r backend/requirements.txt

# Set up your GCP credentials
export GOOGLE_APPLICATION_CREDENTIALS="service-account-key.json"
```

## Running Locally

After setting up your environment and GCP credentials:

```bash
# Start the FastAPI server
cd backend
uvicorn app.main:app --reload
```

Access the API documentation at: http://localhost:8000/docs
```

Create a storage bucket for storing datasets.

Create a secret manager for storing sensitive information.

Create a Cloud Run service for running the application.

Create a Cloud Build trigger for building and deploying the application.


# Using gcloud CLI

# Add storage admin role to the service account
# Grant Firestore permissions for the native-db database

gcloud projects add-iam-policy-binding ultralytics-54321 \
    --member="serviceAccount:ultralytics-challange@ultralytics-54321.iam.gserviceaccount.com" \
    --role="roles/datastore.user"

gcloud projects add-iam-policy-binding ultralytics-54321 \
    --member="serviceAccount:ultralytics-challange@ultralytics-54321.iam.gserviceaccount.com" \
    --role="roles/firebase.admin"

replace 54321 with your ID.