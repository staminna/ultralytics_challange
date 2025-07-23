from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import dataset_routes, model_routes, sample_routes
from .core.config import get_settings

# Application settings
settings = get_settings()

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
app.include_router(dataset_routes.router, prefix=settings.API_V1_STR)
app.include_router(model_routes.router, prefix=settings.API_V1_STR)
app.include_router(sample_routes.router, prefix=settings.API_V1_STR)

@app.get("/")
def root_health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME}

@app.get(f"{settings.API_V1_STR}/health")
def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME}
