"""
API request/response schemas
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class IngestionRequest(BaseModel):
    """Data ingestion request schema"""
    country_name: str
    enabled_sources: Optional[List[str]] = None
    add_to_knowledge_base: bool = False
    use_llm_analysis: bool = False  # Use LLM to analyze and structure data


class IngestionResponse(BaseModel):
    """Data ingestion response schema"""
    status: str
    country_name: str
    enabled_sources: List[str]
    results: Dict[str, int]
    output_files: List[str]
    added_to_kb: bool = False
    message: str

