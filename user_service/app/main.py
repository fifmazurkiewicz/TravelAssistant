"""
FastAPI application entry point
"""
import sys
from pathlib import Path

# Dodaj katalog główny projektu do sys.path (dla importów shared)
current_file = Path(__file__).resolve()
service_root = current_file.parent.parent  # user_service
project_root = service_root.parent  # TravelAssistant
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.config import get_settings

from app.api.v1 import router as api_router

settings = get_settings()

app = FastAPI(
    title="User Service",
    description="User management and authentication service",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "user_service"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

