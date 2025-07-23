from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.v1.routes import dataset_routes
from .core.config import settings
from .core.database import connect_to_mongo, close_mongo_connection

# Application settings
settings = settings

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(dataset_routes.router, prefix="/api/v1", tags=["datasets"])

@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()

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
    return {"status": "ok", "service": settings.PROJECT_NAME}

@app.get(f"{settings.API_V1_STR}/health")
def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME}
