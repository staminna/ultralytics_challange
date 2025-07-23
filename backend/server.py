import uvicorn

from app.main import app

if __name__ == "__main__":
    # Configuration optimized for large file uploads (up to 100GB)
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        timeout_keep_alive=300,  # 5 minutes
        limit_concurrency=10,    # Limit concurrent connections
        limit_max_requests=1000, # Max requests before restart
        log_level="info"
    )
