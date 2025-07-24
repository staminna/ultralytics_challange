# YOLO Dataset Annotation Service

🚀 **Production-ready FastAPI service** for managing and annotating YOLO format datasets with MongoDB backend, chunked upload support, and comprehensive test coverage.

## ✨ Key Features

- **🔥 YOLO11 Integration**: Latest YOLO models with auto-annotation
- **📊 MongoDB Backend**: Scalable document storage with Beanie ODM
- **📤 Chunked Upload**: Support for datasets up to 100GB
- **🧪 90%+ Test Coverage**: Comprehensive unit and integration tests
- **🔄 Batch Processing**: Efficient handling of large datasets
- **🌐 RESTful API**: Complete CRUD operations with OpenAPI docs
- **🐳 Docker Support**: Containerized MongoDB with web interface

## 🚀 Quick Start

```bash
# 1. Clone and setup environment
git clone <repository-url>
cd ultra-assesment
conda env create -f environment.yml
conda activate ultralytics-annotation

# 2. Configure environment
cp .env.example .env
# Edit .env with your settings

# 3. Start services
docker-compose up -d  # MongoDB + mongo-express

# 4. Run the application
cd backend
python -m app.main

# 5. Access services
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
# MongoDB UI: http://localhost:8081
```

## 📋 Table of Contents

- [Installation & Setup](#installation--setup)
- [Environment Configuration](#environment-configuration)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [API Usage](#api-usage)
- [Dataset Management](#dataset-management)
- [Development](#development)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

## 🛠️ Installation & Setup

### Prerequisites

- **Python 3.12+**
- **Conda** (Anaconda/Miniconda)
- **Docker & Docker Compose**
- **Git**

### 1. Environment Setup

**Create and activate conda environment:**
```bash
# Create environment from file
conda env create -f environment.yml

# Activate environment
conda activate ultralytics-annotation

# Verify installation
python --version  # Should be 3.12+
pip list | grep fastapi  # Verify FastAPI installed
```

### Dependency Management

**For Conda (Recommended for Development):**
- Use `environment.yml` - contains all dependencies with proper channels
- Includes development tools (pytest, black, mypy, etc.)
- Better handling of scientific packages (numpy, pytorch)
- No need for `requirements.txt`

**For Docker/Production:**
- Uses `requirements.txt` for pip-based installation
- Optimized for production deployment
- Smaller image size with only runtime dependencies

**For pip-only environments:**
```bash
# If you must use pip instead of conda
pip install -r requirements.txt
```

### 2. Docker Services Setup

**Start MongoDB and mongo-express:**
```bash
# Start services in background
docker-compose up -d

# Check services are running
docker-compose ps

# View logs if needed
docker-compose logs mongodb
docker-compose logs mongo-express
```

### 3. Environment Configuration

**Copy and configure environment file:**
```bash
cp .env.example .env
```

**Edit `.env` file with your settings:**
```bash
# Database Configuration
DATABASE_URL=mongodb://admin:password@localhost:27017
MONGO_DB=dataset_annotation

# Google Cloud Configuration (optional for basic usage)
GCP_PROJECT_ID=your-project-id
GCP_STORAGE_BUCKET=your-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json

# YOLO Configuration
YOLO11_MODEL_PATH=yolo11n.pt
YOLO11_DEFAULT_MODEL=yolo11n.pt
YOLO11_PRODUCTION_MODEL=yolo11m.pt

# API Configuration
API_V1_STR=/api/v1
PROJECT_NAME="YOLO Dataset Annotation Service"
```

## 🏃‍♂️ Running the Application

### Development Mode

```bash
# Activate environment
conda activate ultralytics-annotation

# Start MongoDB services
docker-compose up -d

# Run FastAPI development server
cd backend
python -m app.main

# Or with uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
# Run with production settings
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Access Points

- **API Server**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **MongoDB Web UI**: http://localhost:8081 (admin/password)
- **Health Check**: http://localhost:8000/health

## 🧪 Testing

### Unit Tests

**Run all tests:**
```bash
# Activate environment
conda activate ultralytics-annotation

# Run all tests with coverage
pytest --cov=backend/app --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_final_coverage_push.py -v

# Run tests with detailed output
pytest tests/ -v --tb=short
```

**Test Coverage Analysis:**
```bash
# Generate coverage report
pytest --cov=backend/app --cov-report=html tests/

# View HTML coverage report
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

### Integration Tests

**Run integration tests:**
```bash
# Start services first
docker-compose up -d

# Wait for MongoDB to be ready
sleep 10

# Run integration tests
pytest tests/test_complete_coverage.py -v
pytest tests/test_90_percent_coverage.py -v
```

### Test Suites Overview

| Test File | Purpose | Tests | Coverage |
|-----------|---------|-------|----------|
| `test_final_coverage_push.py` | Core functionality | 22 tests | Services, API routes |
| `test_coverage_final.py` | Utility functions | 12 tests | Utils, config |
| `test_complete_coverage.py` | Comprehensive | 25+ tests | Full application |
| `test_90_percent_coverage.py` | Coverage improvement | 15+ tests | Zero-coverage modules |
| `test_focused_coverage.py` | Module-specific | 20+ tests | Individual modules |
| `test_targeted_coverage.py` | Targeted coverage | 18+ tests | Specific functions |

**Run specific test categories:**
```bash
# Core functionality tests
pytest tests/test_final_coverage_push.py::TestChunkedUploadServiceDetailed -v

# API endpoint tests
pytest tests/test_final_coverage_push.py::TestAPIRoutesComprehensive -v

# Service layer tests
pytest tests/test_final_coverage_push.py::TestServiceMethodsCoverage -v

# Configuration tests
pytest tests/test_coverage_final.py::TestConfigurationCoverageFinal -v
```

## 🌐 API Usage

### Core Endpoints

**Dataset Management:**
```bash
# List all datasets
curl -X GET "http://localhost:8000/api/v1/datasets/"

# Create new dataset
curl -X POST "http://localhost:8000/api/v1/datasets/" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Dataset", "description": "Test dataset"}'

# Get dataset by ID
curl -X GET "http://localhost:8000/api/v1/datasets/{dataset_id}"
```

**Dataset Import:**
```bash
# Import YOLO dataset (small files)
curl -X POST "http://localhost:8000/api/v1/datasets/import/yolo" \
  -F "file=@dataset.zip" \
  -F "dataset_name=My Dataset"

# Chunked upload (large files)
curl -X POST "http://localhost:8000/api/v1/datasets/import/chunked" \
  -F "file=@large_dataset.zip" \
  -F "dataset_name=Large Dataset"
```

**Image Management:**
```bash
# List images in dataset
curl -X GET "http://localhost:8000/api/v1/datasets/{dataset_id}/images"

# Get image details
curl -X GET "http://localhost:8000/api/v1/images/{image_id}"
```

### Interactive API Documentation

Visit http://localhost:8000/docs for interactive Swagger UI documentation with:
- Complete API reference
- Request/response examples
- Try-it-out functionality
- Schema definitions

## 📁 Dataset Management

### Supported Formats

- **YOLO Format**: `.txt` annotation files with `classes.txt`
- **Archive Types**: `.zip`, `.tar`, `.tar.gz`
- **Image Types**: `.jpg`, `.jpeg`, `.png`, `.bmp`
- **Dataset Structure**: Standard YOLO directory layout

### Upload Methods

**1. Script-based Upload:**
```bash
# Upload single dataset
python scripts/import_dataset.py --path /path/to/dataset --name "Dataset Name"

# Bulk upload from directory
python scripts/upload_all_datasets.py --directory /path/to/datasets

# Chunked upload for large files
python scripts/upload_coco_chunked.py --file large_dataset.zip
```

**2. API Upload:**
```bash
# Direct API upload
curl -X POST "http://localhost:8000/api/v1/datasets/import/yolo" \
  -F "file=@dataset.zip" \
  -F "dataset_name=My Dataset"
```

**3. Programmatic Upload:**
```python
import requests

with open('dataset.zip', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/datasets/import/yolo',
        files={'file': f},
        data={'dataset_name': 'My Dataset'}
    )
print(response.json())
```

## 🛠️ Development

### Project Structure

```
ultra-assesment/
├── backend/
│   └── app/
│       ├── api/routes/          # API endpoints
│       ├── core/               # Configuration, database
│       ├── models/             # Data models
│       ├── schemas/            # Pydantic schemas
│       ├── services/           # Business logic
│       └── main.py            # FastAPI application
├── scripts/                   # Utility scripts
├── tests/                     # Test suites
├── docker-compose.yml         # Services configuration
├── environment.yml           # Conda dependencies
└── requirements.txt          # Pip dependencies
```

### Code Quality

**Linting and formatting:**
```bash
# Format code
black backend/app/
isort backend/app/

# Lint code
flake8 backend/app/
mypy backend/app/
```

**Pre-commit hooks:**
```bash
# Install pre-commit
conda install pre-commit

# Setup hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

### Adding New Features

1. **Create feature branch:**
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Add tests first (TDD):**
   ```bash
   # Create test file
   touch tests/test_new_feature.py
   
   # Write failing tests
   pytest tests/test_new_feature.py
   ```

3. **Implement feature:**
   - Add service logic in `backend/app/services/`
   - Add API routes in `backend/app/api/routes/`
   - Add schemas in `backend/app/schemas/`

4. **Verify tests pass:**
   ```bash
   pytest tests/test_new_feature.py -v
   pytest --cov=backend/app
   ```

## 🚀 Deployment

### Docker Deployment

**Build application image:**
```bash
# Build from backend directory (contains Dockerfile)
cd backend
docker build -t yolo-annotation-service .

# Or build from root directory with context
docker build -f backend/Dockerfile -t yolo-annotation-service .
```

**Run with Docker:**
```bash
# Run single container (requires external MongoDB)
docker run -p 8000:8000 \
  -e DATABASE_URL=mongodb://host.docker.internal:27017 \
  yolo-annotation-service

# Or use docker-compose for full stack
docker-compose up -d
```

**Multi-stage production build:**
```bash
# Create production Dockerfile if needed
docker build -f backend/Dockerfile.prod -t yolo-annotation-service:prod .

# Run production container
docker run -d -p 8000:8000 \
  --name yolo-api \
  -e DATABASE_URL=mongodb://prod-mongo:27017 \
  -e ENVIRONMENT=production \
  yolo-annotation-service:prod
```

### Cloud Deployment

**Google Cloud Run:**
```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/PROJECT_ID/yolo-annotation

# Deploy to Cloud Run
gcloud run deploy yolo-annotation \
  --image gcr.io/PROJECT_ID/yolo-annotation \
  --platform managed \
  --region us-central1
```

### Environment Variables for Production

```bash
# Production environment variables
DATABASE_URL=mongodb://user:pass@prod-mongodb:27017
GCP_PROJECT_ID=production-project
GCP_STORAGE_BUCKET=prod-datasets-bucket
ENVIRONMENT=production
LOG_LEVEL=INFO
```

## 🔧 Troubleshooting

### Common Issues

**1. Conda Environment Issues:**
```bash
# Remove and recreate environment
conda env remove -n ultralytics-annotation
conda env create -f environment.yml
conda activate ultralytics-annotation
```

**2. MongoDB Connection Issues:**
```bash
# Check MongoDB status
docker-compose ps
docker-compose logs mongodb

# Restart MongoDB
docker-compose restart mongodb

# Reset MongoDB data
docker-compose down -v
docker-compose up -d
```

**3. Port Conflicts:**
```bash
# Check what's using port 8000
lsof -i :8000

# Kill process if needed
kill -9 <PID>

# Or use different port
uvicorn app.main:app --port 8001
```

**4. Test Failures:**
```bash
# Clear pytest cache
pytest --cache-clear

# Run tests with verbose output
pytest -v --tb=long

# Run specific failing test
pytest tests/test_file.py::test_function -v
```

**5. Import Errors:**
```bash
# Verify Python path
echo $PYTHONPATH

# Add current directory to path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or run from correct directory
cd backend
python -m app.main
```

### Performance Optimization

**Database Indexing:**
```python
# MongoDB indexes are created automatically
# Check index status in mongo-express at localhost:8081
```

**Memory Usage:**
```bash
# Monitor memory usage
docker stats

# Limit container memory
docker-compose up -d --memory="2g"
```

### Logging and Monitoring

**Application logs:**
```bash
# View application logs
tail -f logs/app.log

# Docker logs
docker-compose logs -f api
```

**Health checks:**
```bash
# API health check
curl http://localhost:8000/health

# Database health check
curl http://localhost:8000/api/v1/health/db
```

## 📚 Additional Resources

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **YOLO11 Documentation**: https://docs.ultralytics.com/
- **MongoDB Documentation**: https://docs.mongodb.com/
- **Beanie ODM**: https://beanie-odm.dev/
- **Pytest Documentation**: https://docs.pytest.org/

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for new functionality
4. Ensure all tests pass (`pytest`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**🎯 Ready to get started?** Follow the [Quick Start](#-quick-start) guide above!
