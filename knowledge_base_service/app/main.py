"""
FastAPI application entry point
"""
import logging
import sys
from pathlib import Path

# Dodaj katalog serwisu do sys.path (dla importów config i exceptions)
current_file = Path(__file__).resolve()
service_root = current_file.parent.parent  # knowledge_base_service
if str(service_root) not in sys.path:
    sys.path.insert(0, str(service_root))

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as api_router
from config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events - initialize services on startup"""
    # Startup: Initialize services
    try:
        from infrastructure.adapters.knowledge_base_adapter import KnowledgeBaseReader
        
        # Initialize knowledge base reader
        # Vector store collection will be auto-created on first use
        # BM25 index will be built incrementally as documents are added
        kb_reader = KnowledgeBaseReader()
        print("✅ Knowledge Base Service initialized (native async Qdrant)")
    except Exception as e:
        print(f"⚠️  Warning: Could not initialize services: {e}")
        print("Services will be initialized on first use.")
    
    yield
    
    # Shutdown: cleanup async connections
    try:
        from infrastructure.adapters.vector_store.qdrant_adapter import QdrantVectorStore
        from infrastructure.adapters.vector_store.vector_store_factory import VectorStoreFactory
        
        vector_store = VectorStoreFactory.create()
        # Close async Qdrant client if it's QdrantVectorStore
        if isinstance(vector_store, QdrantVectorStore) and hasattr(vector_store, 'close'):
            await vector_store.close()
    except Exception:
        pass  # Ignore cleanup errors


app = FastAPI(
    title="Knowledge Base Service",
    description="RAG and knowledge base management service with hybrid search (BM25 + Vector) for Polish",
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
        "service": "knowledge_base_service",
        "features": {
            "hybrid_search": settings.use_hybrid_search,
            "embedding_model": settings.embedding_model,
            "vector_db": settings.vector_db_type
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)

