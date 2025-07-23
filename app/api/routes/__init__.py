from .dataset_routes import router as dataset_router

# Export the router to be included in the main FastAPI app
__all__ = ["dataset_router"]
