from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .api.routes import (
    dataset_management_routes,
    image_management_routes,
    label_management_routes,
    dataset_import_routes
)
from .core.config import settings
from .core.database import connect_to_mongo, close_mongo_connection

# Application settings
settings = settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()

# Initialize FastAPI app with configuration for large file uploads
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    # Configure for large file uploads (up to 100GB)
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes - now split into focused modules
app.include_router(dataset_management_routes.router, prefix="/api/v1")
app.include_router(image_management_routes.router, prefix="/api/v1")
app.include_router(label_management_routes.router, prefix="/api/v1")
app.include_router(dataset_import_routes.router, prefix="/api/v1")



# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/")
def root_health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
