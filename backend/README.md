# Dataset Annotation Tool

A comprehensive tool for importing, managing, and annotating datasets in YOLO format, designed to integrate with GCP infrastructure (Firestore and Cloud Storage).

## Setup

### Environment Setup

1. This project uses conda for environment management. Make sure you have conda installed.

2. Create the conda environment from the provided `environment.yaml` file:
   ```bash
   conda env create -f environment.yaml
   ```

3. Activate the conda environment:
   ```bash
   conda activate dataset-annotation
   ```

4. Ensure all Python dependencies are installed:
   ```bash
   pip install -r requirements.txt
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

#### Importing a Custom YOLO Dataset

To upload your own custom YOLO dataset, ensure it is structured correctly (images and labels in their respective directories) and then compress it into a `.zip` file. Once zipped, you can use the `dataset-tool.sh` or `import.py` script to import it. This process will upload your dataset to Google Cloud Storage and store its metadata (including image and label information) in Google Datastore/Firestore.

Example using `dataset-tool.sh`:

```bash
./dataset-tool.sh import /path/to/your_custom_dataset.zip "My Custom Dataset" --description="A dataset of custom objects" --classes=object1,object2,object3
```

- Replace `/path/to/your_custom_dataset.zip` with the actual path to your zipped YOLO dataset.
- Replace `"My Custom Dataset"` with a descriptive name for your dataset.
- Adjust `--description` and `--classes` as per your dataset's content. The `--classes` argument should be a comma-separated list of class names present in your dataset.

## Running with Docker Compose

To run the entire application, including the backend server and a MongoDB instance, using Docker Compose:

1.  **Ensure Docker is installed:** Make sure you have Docker and Docker Compose installed on your system.

2.  **Build and run the services:** From the project root directory, execute:
    ```bash
    docker-compose up --build
    ```
    This command will:
    -   Build the `backend` service's Docker image using the `Dockerfile`.
    -   Pull the `mongo:latest` image for the `mongodb` service.
    -   Start both services. The backend will be accessible at `http://localhost:8000`.

3.  **MongoDB Integration:** The backend service is configured to connect to the `mongodb` service within the Docker network. The `MONGO_URI` environment variable in `docker-compose.yml` is set to `mongodb://mongodb:27017/mydatabase` to facilitate this connection.

4.  **Stopping the services:** To stop the running containers, press `Ctrl+C` in the terminal where `docker-compose up` is running. To stop and remove the containers, networks, and volumes (including MongoDB data), run:
    ```bash
    docker-compose down -v
    ```

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
- `docker-compose.yml` - Docker Compose configuration for running the application and MongoDB

## Troubleshooting

- **Missing dependencies**: If you encounter missing modules, install them with `pip install <module_name>`
- **API connection issues**: Ensure the server is running and accessible at the configured URL
- **Authentication errors**: Verify your GCP credentials are correctly set up

## Testing and Verification

To verify that the core requirements are met, follow these steps:

### 1. Import a Dataset in YOLO Format

Use the provided `sample-import.sh` script to import a test dataset. This script will create a small YOLO dataset, package it, and import it using the `dataset-tool.sh` wrapper.

```bash
./sample-import.sh
```

After running, you should see output indicating the dataset has been imported.

### 2. List Datasets

To confirm the dataset was successfully imported and is listed, use the `list` command:

```bash
./dataset-tool.sh list
```

This should display a list of all imported datasets, including the one you just imported.

### 3. List Images with Labels for a Specific Dataset

Once you have the `DATASET_ID` from the `list` command, you can retrieve the images and their labels for that dataset:

```bash
./dataset-tool.sh images <DATASET_ID>
```

Replace `<DATASET_ID>` with the actual ID of the dataset you want to inspect. This command should output a list of images within the specified dataset, along with their associated labels.

## License

This project is proprietary and confidential.