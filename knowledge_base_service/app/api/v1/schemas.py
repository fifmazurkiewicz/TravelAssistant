"""
API request/response schemas
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    """Document response schema"""
    id: int
    filename: str
    content_type: Optional[str] = None
    file_size: int
    created_at: datetime


class DocumentUploadResponse(BaseModel):
    """Document upload response schema"""
    document_id: int
    filename: str
    status: str
    message: str


class SearchRequest(BaseModel):
    """Search request schema"""
    query: str
    filters: Optional[Dict[str, Any]] = None
    search_type: Optional[str] = "hybrid"  # "hybrid", "vector", "bm25"


class SearchResult(BaseModel):
    """Search result schema"""
    content: str
    metadata: Optional[Dict[str, Any]] = None
    score: float


class SearchResponse(BaseModel):
    """Search response schema"""
    query: str
    results: List[SearchResult]
    total_results: int


# Memory Schemas
class ConversationMessageResponse(BaseModel):
    """Conversation message response schema"""
    role: str  # "user" | "assistant"
    content: str
    timestamp: Optional[datetime] = None


class ConversationMemoryResponse(BaseModel):
    """Conversation memory response schema"""
    user_id: int
    session_id: str
    messages: List[ConversationMessageResponse]
    total_messages: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserPreferencesResponse(BaseModel):
    """User preferences response schema"""
    user_id: int
    preferences: Dict[str, Any]  # {"travel_style": "adventure", "budget": "low", ...}
    favorite_destinations: List[str]
    travel_history: List[Dict[str, Any]]
    updated_at: Optional[datetime] = None


# Chat Schemas
class ChatRequest(BaseModel):
    """Chat request schema"""
    query: str
    filters: Optional[Dict[str, Any]] = None
    conversation_history: Optional[List[Dict[str, str]]] = None  # List of {"role": "user|assistant", "content": "..."}


class ChatResponse(BaseModel):
    """Chat response schema with LLM-generated answer"""
    query: str
    response: str  # LLM-generated response
    sources: List[SearchResult]  # Source documents used for generation
    total_sources: int