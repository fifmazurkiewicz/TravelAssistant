"""
Search result entity
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class SearchResult:
    """Search result value object"""
    content: str
    metadata: Optional[Dict[str, Any]] = None
    score: float = 0.0
    document_id: Optional[int] = None
    chunk_id: Optional[int] = None

