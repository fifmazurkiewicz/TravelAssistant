"""
Knowledge base reader port (interface) - Read operations only
Note: Write operations are handled by Knowledge Management Service
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from domain.entities.search_result import SearchResult


class IKnowledgeBaseReader(ABC):
    """Knowledge base reader interface - only read operations (CQS Query)"""
    
    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        search_type: Optional[str] = None,  # "vector", "bm25", "hybrid"
        user_id: Optional[int] = None,  # Filter by user_id
        include_global: bool = True  # Include global documents in user search
    ) -> List[SearchResult]:
        """Search knowledge base using hybrid search (BM25 + Vector)"""
        pass

