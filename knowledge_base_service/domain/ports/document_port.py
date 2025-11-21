"""
Document repository port (interface)
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from domain.entities.document import Document


class IDocumentRepository(ABC):
    """Document repository interface"""
    
    @abstractmethod
    async def create(self, document: Document) -> Document:
        """Create new document"""
        pass
    
    @abstractmethod
    async def get_by_id(self, document_id: int) -> Optional[Document]:
        """Get document by ID"""
        pass
    
    @abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> List[Document]:
        """List all documents"""
        pass
    
    @abstractmethod
    async def delete(self, document_id: int) -> bool:
        """Delete document"""
        pass

