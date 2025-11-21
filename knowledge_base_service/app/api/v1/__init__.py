"""
API v1 routes
"""
from fastapi import APIRouter

from app.api.v1 import documents, memory, search, test_data

router = APIRouter()

router.include_router(documents.router, prefix="/documents", tags=["documents"])
router.include_router(search.router, prefix="/search", tags=["search"])
router.include_router(test_data.router, prefix="/test", tags=["test"])
router.include_router(memory.router)  # Memory endpoints (prefix już w memory.py)
# Data ingestion is a separate service, not part of knowledge_base_service

