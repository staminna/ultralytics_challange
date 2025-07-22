# Dataset Annotation Tool

A comprehensive tool for importing, managing, and annotating datasets in YOLO format, designed to integrate with GCP infrastructure (Firestore and Cloud Storage).

## Setup

### Environment Setup

1. This project uses conda for environment management. Make sure you have conda installed.

2. Create and activate the conda environment:
   ```bash
   conda create -n dataset-annotation python=3.12
   conda activate dataset-annotation
   ```

3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   
   If you encounter missing dependencies like `pydantic-settings`, install them manually:
   ```bash
   pip install pydantic-settings
   ```

### GCP Configuration

1. Place your GCP service account key in `service-account-key.json` in the project root.

2. Set up environment variables (can be added to a `.env` file):
   ```
   GCP_PROJECT_ID=your-gcp-project-id
   GCP_STORAGE_BUCKET=your-gcp-storage-bucket
   ```

## Usage

### Starting the Server

1. Start the FastAPI backend server:
   ```bash
   conda activate dataset-annotation
   python server.py
   ```

2. The server will be accessible at `http://localhost:8000` with API endpoints at `/api/v1/datasets/...`

### Dataset Import Tool

The project includes a Python client (`import.py`) and shell wrapper (`dataset-tool.sh`) for easy interaction with the API.

#### Shell Wrapper Usage

```bash
# Import a dataset
./dataset-tool.sh import path/to/dataset.zip "Dataset Name" --description="Dataset description" --classes=car,person,bicycle

# List all datasets
./dataset-tool.sh list

# List images in a dataset
./dataset-tool.sh images DATASET_ID

# Check import status
./dataset-tool.sh status DATASET_ID
```

#### Direct Python Client Usage

```bash
# Import a dataset
./import.py import --path=path/to/dataset.zip --name="Dataset Name" --description="Dataset description" --classes=car,person,bicycle

# List all datasets
./import.py list

# List images in a dataset
./import.py images --dataset-id=DATASET_ID

# Check import status
./import.py status --dataset-id=DATASET_ID
```

#### Sample Import Script

A sample import script is included to demonstrate the workflow:

```bash
./sample-import.sh
```

This script:
1. Creates a small test YOLO dataset with dummy images and labels
2. Packages it into a ZIP file
3. Imports it using the dataset-tool.sh wrapper
4. Lists the imported dataset

## API Documentation

Access the API docs:
Swagger UI: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc

For detailed API documentation, refer to `API_DOCUMENTATION.md`.

## Project Structure

- `app/` - FastAPI backend code
  - `api/` - API routes and controllers
  - `core/` - Core configurations
  - `models/` - Data models
  - `services/` - Business logic
- `import.py` - Python client for dataset operations
- `dataset-tool.sh` - Shell wrapper for the Python client
- `server.py` - FastAPI server startup script
- `sample-import.sh` - Sample import demonstration script
- `requirements.txt` - Python dependencies
- `service-account-key.json` - GCP service account credentials

## Troubleshooting

- **Missing dependencies**: If you encounter missing modules, install them with `pip install <module_name>`
- **API connection issues**: Ensure the server is running and accessible at the configured URL
- **Authentication errors**: Verify your GCP credentials are correctly set up

## License

This project is proprietary and confidential.
