"""
API v1 routes
"""
from fastapi import APIRouter

from app.api.v1 import ingestion

router = APIRouter()

router.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])

