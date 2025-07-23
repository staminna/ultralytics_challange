# Dataset Setup Guide

This document describes how to download and set up YOLO datasets for the project.

## Available Scripts

### `backend/scripts/download_coco_to_backend.py`

Downloads COCO datasets directly to the `backend/datasets/` directory using YOLO CLI.

**Usage:**
```bash
cd backend/scripts
python download_coco_to_backend.py
```

**What it does:**
1. Creates the necessary directory structure in `backend/datasets/`
2. Downloads COCO8 (8 images) and COCO128 (128 images) datasets
3. Moves datasets from the default YOLO location to our backend folder
4. Creates YAML configuration files in `backend/datasets/raw/`
5. Displays dataset structure and statistics

## Dataset Structure

After running the script, your datasets will be organized as:

```
backend/datasets/
├── raw/
│   ├── coco8.yaml      # COCO8 configuration
│   └── coco128.yaml    # COCO128 configuration
├── coco8/
│   ├── images/
│   │   ├── train/      # 4 training images
│   │   └── val/        # 4 validation images
│   └── labels/
│       ├── train/      # 4 training labels
│       └── val/        # 4 validation labels
└── coco128/
    ├── images/
    │   └── train2017/  # 128 images
    └── labels/
        └── train2017/  # 128 labels
```

## Dataset Information

- **COCO8**: Small dataset with 8 images (4 train, 4 val) - perfect for testing
- **COCO128**: Medium dataset with 128 images - good for development and validation
- Both datasets contain 80 COCO classes (person, bicycle, car, etc.)

## Integration with Backend

The datasets are now ready to be used with your existing backend services:

1. **Dataset Import**: Use the existing YOLO import service to process these datasets
2. **Training**: Use the YAML files in `raw/` for YOLO training
3. **Testing**: Perfect for testing the annotation service functionality

## Requirements

- Python 3.8+
- ultralytics package (`pip install ultralytics`)
- Sufficient disk space (COCO8: ~1MB, COCO128: ~6MB)

## Troubleshooting

If you encounter issues:

1. **Permission errors**: Ensure write permissions to the backend/datasets directory
2. **Network issues**: Check internet connection for dataset downloads
3. **YOLO CLI errors**: Update ultralytics with `pip install -U ultralytics`

## Next Steps

1. Test the datasets with your existing backend services
2. Use these datasets to validate the YOLO import functionality
3. Consider downloading larger datasets (COCO2017) if needed for production
