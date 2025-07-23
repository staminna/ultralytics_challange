# YOLO Dataset Management API Documentation

This document provides comprehensive instructions for using the YOLO Dataset Management API to import datasets, list datasets, and retrieve images with labels.

## 🚀 Quick Start

### Prerequisites
1. **Start the Server**
   ```bash
   cd backend
   python server.py
   ```
   The server will run on `http://localhost:8000`

2. **Access API Documentation**
   - Interactive docs: `http://localhost:8000/docs`
   - OpenAPI spec: `http://localhost:8000/api/v1/openapi.json`

## 📊 API Endpoints Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/datasets/import/yolo` | POST | Import YOLO dataset from ZIP file |
| `/api/v1/datasets/` | GET | List all datasets with pagination |
| `/api/v1/datasets/{dataset_id}` | GET | Get specific dataset details |
| `/api/v1/datasets/{dataset_id}/images` | GET | List images with labels for dataset |
| `/api/v1/datasets/{dataset_id}/import/status` | GET | Check import/processing status |

---

## 1. 📦 Import a Dataset in YOLO Format

### Endpoint
```
POST /api/v1/datasets/import/yolo
```

### Description
Import a YOLO dataset from a ZIP file. Supports large datasets up to 100GB with automatic chunked processing.

### Request Format
```bash
curl -X POST "http://localhost:8000/api/v1/datasets/import/yolo" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_dataset.zip" \
  -F "dataset_name=My Dataset Name"
```

### Parameters
- **file** (required): ZIP file containing YOLO dataset
- **dataset_name** (optional): Custom name for the dataset

### YOLO Dataset Structure
Your ZIP file should contain:
```
dataset.zip
├── images/
│   ├── train/
│   │   ├── image1.jpg
│   │   └── image2.jpg
│   └── val/
│       ├── image3.jpg
│       └── image4.jpg
├── labels/
│   ├── train/
│   │   ├── image1.txt
│   │   └── image2.txt
│   └── val/
│       ├── image3.txt
│       └── image4.txt
├── classes.txt (optional)
└── data.yaml (optional)
```

### Example Usage

#### Basic Import
```bash
curl -X POST "http://localhost:8000/api/v1/datasets/import/yolo" \
  -F "file=@coco8.zip" \
  -F "dataset_name=COCO8 Dataset"
```

#### Large Dataset Import
```bash
curl -X POST "http://localhost:8000/api/v1/datasets/import/yolo" \
  -F "file=@large_dataset.zip" \
  -F "dataset_name=Large YOLO Dataset" \
  --max-time 3600
```

### Response Format
```json
{
  "id": "507f1f77bcf86cd799439011",
  "name": "COCO8 Dataset",
  "description": "YOLO dataset imported from coco8.zip",
  "format": "yolo",
  "file_hash": "abc123def456...",
  "processing_status": "completed",
  "images_count": 8,
  "labels_count": 6,
  "processed_images": 8,
  "classes_count": 80,
  "original_filename": "coco8.zip"
}
```

### Status Values
- **processing**: Dataset is being processed
- **completed**: Import successful
- **failed**: Import failed (check logs)

---

## 2. 📋 List Datasets

### Endpoint
```
GET /api/v1/datasets/
```

### Description
Retrieve a paginated list of all imported datasets.

### Request Format
```bash
curl -X GET "http://localhost:8000/api/v1/datasets/?skip=0&limit=10"
```

### Parameters
- **skip** (optional): Number of records to skip (default: 0)
- **limit** (optional): Maximum records to return (default: 10)

### Example Usage

#### List All Datasets
```bash
curl -X GET "http://localhost:8000/api/v1/datasets/"
```

#### Paginated Request
```bash
curl -X GET "http://localhost:8000/api/v1/datasets/?skip=10&limit=5"
```

### Response Format
```json
[
  {
    "id": "507f1f77bcf86cd799439011",
    "name": "COCO8 Dataset",
    "description": "YOLO dataset imported from coco8.zip",
    "format": "yolo",
    "file_hash": "abc123def456...",
    "gcs_path": "datasets/507f1f77bcf86cd799439011/",
    "metadata": {
      "processing_status": "completed",
      "images_count": 8,
      "labels_count": 6,
      "processed_images": 8
    },
    "images": [],
    "classes": []
  }
]
```

---

## 3. 🖼️ List Images with Labels for a Specific Dataset

### Endpoint
```
GET /api/v1/datasets/{dataset_id}/images
```

### Description
Retrieve images and their associated labels for a specific dataset with pagination support.

### Request Format
```bash
curl -X GET "http://localhost:8000/api/v1/datasets/{dataset_id}/images?skip=0&limit=10"
```

### Parameters
- **dataset_id** (required): Dataset ID from import response
- **skip** (optional): Number of images to skip (default: 0)
- **limit** (optional): Maximum images to return (default: 10)

### Example Usage

#### Get All Images for Dataset
```bash
curl -X GET "http://localhost:8000/api/v1/datasets/507f1f77bcf86cd799439011/images"
```

#### Paginated Images Request
```bash
curl -X GET "http://localhost:8000/api/v1/datasets/507f1f77bcf86cd799439011/images?skip=0&limit=5"
```

### Response Format
```json
[
  {
    "id": "507f1f77bcf86cd799439012",
    "dataset_id": "507f1f77bcf86cd799439011",
    "file_name": "image1.jpg",
    "gcs_path": "datasets/507f1f77bcf86cd799439011/images/image1.jpg",
    "width": 640,
    "height": 480,
    "labels": [
      {
        "id": "507f1f77bcf86cd799439013",
        "class_id": "507f1f77bcf86cd799439014",
        "x_center": 0.5,
        "y_center": 0.3,
        "width": 0.2,
        "height": 0.4
      }
    ]
  }
]
```

---

## 🔍 Additional Endpoints

### Get Specific Dataset
```bash
curl -X GET "http://localhost:8000/api/v1/datasets/507f1f77bcf86cd799439011"
```

### Check Import Status
```bash
curl -X GET "http://localhost:8000/api/v1/datasets/507f1f77bcf86cd799439011/import/status"
```

---

## 🛠️ Complete Workflow Example

Here's a complete example workflow:

### Step 1: Import Dataset
```bash
# Import a YOLO dataset
curl -X POST "http://localhost:8000/api/v1/datasets/import/yolo" \
  -F "file=@my_dataset.zip" \
  -F "dataset_name=My Custom Dataset"

# Response will include dataset_id
# {"id": "507f1f77bcf86cd799439011", ...}
```

### Step 2: List All Datasets
```bash
# Verify the dataset was imported
curl -X GET "http://localhost:8000/api/v1/datasets/"
```

### Step 3: Get Images with Labels
```bash
# Use the dataset_id from step 1
curl -X GET "http://localhost:8000/api/v1/datasets/507f1f77bcf86cd799439011/images"
```

---

## 📊 Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created (for imports) |
| 400 | Bad Request (invalid dataset format) |
| 404 | Dataset not found |
| 422 | Validation Error |
| 500 | Internal Server Error |

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Import Fails with "Invalid YOLO dataset"
- Ensure your ZIP contains `images/` and optionally `labels/` directories
- Check that image files are in supported formats (jpg, jpeg, png, bmp, tiff)
- Verify label files are in YOLO format (.txt)

#### 2. Large Dataset Timeout
- Use `--max-time 3600` in curl for large uploads
- Check server logs for processing progress
- Use the status endpoint to monitor progress

#### 3. Dataset Not Found
- Verify the dataset_id from the import response
- Check that the import completed successfully

### Server Logs
Monitor server logs for detailed error information:
```bash
# In the backend directory
python server.py
```

---

## 🚀 Performance Tips

1. **Large Datasets**: The system automatically uses chunked processing for datasets with many images
2. **Pagination**: Use appropriate `skip` and `limit` parameters for large result sets
3. **Monitoring**: Use the status endpoint to track import progress
4. **Storage**: Images are stored efficiently with consistent directory structure

---

## 📝 Notes

- Dataset IDs are MongoDB ObjectIds converted to strings
- Images without labels are supported (for annotation purposes)
- The system supports both local and Google Cloud Storage backends
- All coordinates in labels are normalized (0.0 to 1.0)
- The API automatically handles duplicate detection during import
