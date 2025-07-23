from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import dataset_router

app = FastAPI(
    title="YOLO Dataset Annotation Service",
    description="A service for managing and annotating YOLO format datasets",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(
    dataset_router,
    prefix="/api/v1/datasets",
    tags=["datasets"]
)

@app.get("/")
async def root():
    return {"message": "YOLO Dataset Annotation Service is running"}
