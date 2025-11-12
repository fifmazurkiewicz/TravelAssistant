"""
FastAPI application entry point for Data Ingestion Service
"""
import sys
from pathlib import Path

# Dodaj katalog serwisu do sys.path (dla importów config i exceptions)
current_file = Path(__file__).resolve()
service_root = current_file.parent.parent  # data_ingestion_service
if str(service_root) not in sys.path:
    sys.path.insert(0, str(service_root))

# Dodaj katalog research do sys.path (dla importów data_ingestion)
project_root = service_root.parent  # TravelAssistant
research_path = project_root / "research"
if str(research_path) not in sys.path:
    sys.path.insert(0, str(research_path))

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as api_router
from config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events"""
    # Startup
    print("✅ Data Ingestion Service initialized")
    yield
    # Shutdown
    print("👋 Data Ingestion Service shutting down")


app = FastAPI(
    title="Data Ingestion Service",
    description="Service for fetching travel data from external sources (Wikipedia, Wikidata, TripAdvisor, etc.)",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
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
    return {
        "status": "healthy",
        "service": "data_ingestion_service",
        "output_dir": settings.output_dir
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)

