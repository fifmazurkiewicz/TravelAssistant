"""
Vector store port (interface) - for swappable vector databases
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class IVectorStore(ABC):
    """Vector store interface for swappable implementations"""
    
    @abstractmethod
    async def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """Add documents to vector store"""
        pass
    
    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        query_text: Optional[str] = None,
        use_hybrid: bool = True
    ) -> List[Dict[str, Any]]:
        """Search vector store with optional hybrid search (dense + sparse)"""
        pass
    
    @abstractmethod
    async def delete(self, ids: List[str]) -> bool:
        """Delete documents from vector store"""
        pass
    
    async def scroll_all(
        self,
        limit: int = 10000,
        with_payload: bool = True,
        with_vectors: bool = False
    ) -> List[Dict[str, Any]]:
        """Scroll through all points in collection (optional - not all implementations may support this)"""
        raise NotImplementedError("scroll_all not implemented for this vector store")
    
    @abstractmethod
    async def create_collection(self, collection_name: str) -> bool:
        """Create collection"""
        pass
    
    @abstractmethod
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete collection"""
        pass

