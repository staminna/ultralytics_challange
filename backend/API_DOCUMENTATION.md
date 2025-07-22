# Dataset Annotation Backend API Documentation

## Overview

This API provides core functionality for a dataset annotation service, supporting the import, listing, and management of datasets in YOLO format, with a particular focus on handling large datasets up to 100GB in size.

## Architecture

- **Backend Framework**: FastAPI
- **Database**: Firestore (GCP)
- **Storage**: Cloud Storage (GCP)
- **Authentication**: Service Account Key (GCP)

## Requirements

- Python 3.12
- Conda environment: `dataset-annotation`
- GCP service account key (`service-account-key.json`)
- Environment variables:
  - `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account key file
  - `GCP_PROJECT_ID`: Google Cloud Platform project ID
  - `GCP_STORAGE_BUCKET`: Cloud Storage bucket name

## Running the API

From the `backend` directory, run:

```bash
uvicorn app.main:app --reload
```

## Core API Endpoints

### 1. Import Dataset in YOLO Format

#### Small Datasets (< 100MB)

```http
POST /api/v1/import/yolo
```

**Form Parameters:**
- `dataset_name`: Name of the dataset (required)
- `description`: Description of the dataset (optional)
- `class_names`: List of class names for YOLO labels (optional)
- `zip_file`: ZIP file containing YOLO dataset (required)

**ZIP File Structure:**
- `images/` directory with image files
- `labels/` directory with YOLO format label files (.txt)
- (optional) `classes.txt` with class names

**Response:**
```json
{
  "id": "dataset-uuid",
  "name": "traffic_signs",
  "description": "Traffic sign dataset",
  "storage_path": "datasets/dataset-uuid",
  "created_at": "2025-07-21T12:34:56",
  "updated_at": "2025-07-21T12:34:56",
  "status": "ready",
  "import_progress": 100,
  "image_count": 0,
  "error_message": null,
  "upload_id": null,
  "size_bytes": 5000000
}
```

#### Large Datasets (≥ 100MB)

**1. Create the dataset record:**
```http
POST /api/v1/
```

**Request Body:**
```json
{
  "name": "traffic_signs_large",
  "description": "Large traffic sign dataset"
}
```

**2. Upload chunks sequentially:**
```http
POST /api/v1/import/yolo/chunk
```

**Form Parameters:**
- `dataset_id`: ID of the created dataset
- `upload_id`: ID from the first chunk response
- `chunk_number`: Index of this chunk (0-based)
- `total_chunks`: Total number of chunks
- `chunk_file`: Binary chunk data (part of the ZIP file)

**Response:**
```json
{
  "upload_id": "upload-uuid",
  "dataset_id": "dataset-uuid",
  "chunk_number": 1,
  "total_chunks": 10,
  "status": "uploading"
}
```

**3. Check import status:**
```http
GET /api/v1/import/status/{dataset_id}
```

**Response:**
```json
{
  "dataset_id": "dataset-uuid",
  "status": "importing",
  "import_progress": 45,
  "image_count": 127,
  "error_message": null,
  "started_at": "2025-07-21T12:34:56",
  "estimated_completion": "2025-07-21T12:45:00"
}
```

### 2. List Datasets

```http
GET /api/v1/
```

**Query Parameters:**
- `limit`: Maximum number of datasets to return (default: 100)
- `offset`: Number of datasets to skip for pagination (default: 0)

**Response:**
```json
{
  "datasets": [
    {
      "id": "dataset-uuid",
      "name": "traffic_signs",
      "description": "Traffic sign dataset",
      "storage_path": "datasets/dataset-uuid",
      "created_at": "2025-07-21T12:34:56",
      "updated_at": "2025-07-21T12:34:56",
      "image_count": 250,
      "status": "ready",
      "import_progress": 100,
      "error_message": null,
      "upload_id": null,
      "size_bytes": 25000000
    }
  ],
  "total": 45
}
```

### 3. List Images with Labels for a Dataset

```http
GET /api/v1/{dataset_id}/images
```

**Query Parameters:**
- `limit`: Maximum number of images to return (default: 100)
- `offset`: Number of images to skip for pagination (default: 0)

**Response:**
```json
{
  "images": [
    {
      "id": "image-uuid",
      "filename": "stop_sign_1.jpg",
      "dataset_id": "dataset-uuid",
      "storage_path": "datasets/dataset-uuid/images/stop_sign_1.jpg",
      "width": 640,
      "height": 480,
      "created_at": "2025-07-21T12:34:56",
      "updated_at": "2025-07-21T12:34:56",
      "download_url": "https://storage.googleapis.com/...",
      "labels": [
        {
          "id": "label-uuid",
          "image_id": "image-uuid",
          "class_id": 0,
          "x_center": 0.5,
          "y_center": 0.5,
          "width": 0.3,
          "height": 0.4,
          "created_at": "2025-07-21T12:34:56",
          "updated_at": "2025-07-21T12:34:56"
        }
      ]
    }
  ],
  "total": 250,
  "dataset_id": "dataset-uuid"
}
```

## Data Models

### Dataset

| Field           | Type      | Description                                     |
|----------------|-----------|-------------------------------------------------|
| id             | string    | Unique identifier                               |
| name           | string    | Dataset name                                    |
| description    | string    | Dataset description                             |
| storage_path   | string    | Path in Cloud Storage                           |
| created_at     | datetime  | Creation timestamp                              |
| updated_at     | datetime  | Last update timestamp                           |
| status         | string    | Status: pending, importing, finalizing, ready, error |
| import_progress| int       | Import progress percentage (0-100)              |
| error_message  | string    | Error message if status is "error"              |
| image_count    | int       | Number of images in dataset                     |
| upload_id      | string    | ID for chunked uploads                          |
| size_bytes     | int       | Total size of dataset in bytes                  |

### Image

| Field         | Type      | Description                                     |
|--------------|-----------|-------------------------------------------------|
| id           | string    | Unique identifier                               |
| filename     | string    | Original filename                               |
| dataset_id   | string    | Parent dataset ID                               |
| storage_path | string    | Path in Cloud Storage                           |
| width        | int       | Image width in pixels                           |
| height       | int       | Image height in pixels                          |
| created_at   | datetime  | Creation timestamp                              |
| updated_at   | datetime  | Last update timestamp                           |
| download_url | string    | Signed URL for image access                     |
| labels       | Label[]   | Array of associated labels                      |

### Label

| Field       | Type      | Description                                     |
|------------|-----------|-------------------------------------------------|
| id         | string    | Unique identifier                               |
| image_id   | string    | Parent image ID                                 |
| class_id   | int       | Class identifier                                |
| x_center   | float     | Normalized x-center of bounding box (0-1)       |
| y_center   | float     | Normalized y-center of bounding box (0-1)       |
| width      | float     | Normalized width of bounding box (0-1)          |
| height     | float     | Normalized height of bounding box (0-1)         |
| created_at | datetime  | Creation timestamp                              |
| updated_at | datetime  | Last update timestamp                           |

### Class Definition

| Field       | Type      | Description                                     |
|------------|-----------|-------------------------------------------------|
| id         | string    | Unique identifier                               |
| dataset_id | string    | Parent dataset ID                               |
| class_id   | int       | Class identifier                                |
| name       | string    | Class name                                      |
| created_at | datetime  | Creation timestamp                              |
| updated_at | datetime  | Last update timestamp                           |

## Error Handling

The API returns standard HTTP status codes:

| Code | Description                                         |
|------|-----------------------------------------------------|
| 200  | Success                                             |
| 201  | Created (for POST operations)                       |
| 400  | Bad Request (invalid input)                         |
| 404  | Not Found (resource doesn't exist)                  |
| 500  | Server Error                                        |

Error responses include a JSON body with an error message:

```json
{
  "detail": "Error message describing the issue"
}
```

## Handling Large Datasets

For datasets up to 100GB, the system uses:

1. **Chunked Uploads**: Breaks large files into manageable chunks
2. **Background Processing**: Uses FastAPI's BackgroundTasks
3. **Batch Processing**: Processes images and labels in batches
4. **Status Tracking**: Provides progress updates via status endpoint
5. **Cloud Storage Composition**: Efficiently reassembles chunks

## Notes

- The download_url for images contains a signed URL valid for 1 hour
- Large dataset imports process asynchronously in the background
- The API requires proper GCP authentication via service account key
- YOLO format requires normalized bounding box coordinates (0-1)
- The system automatically handles ZIP extraction and validation
