"""
Document processor port (interface)
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities.document import Document, DocumentChunk


class IDocumentProcessor(ABC):
    """Document processor interface"""
    
    @abstractmethod
    async def process_document(
        self,
        filename: str,
        content: bytes,
        content_type: Optional[str] = None
    ) -> Document:
        """Process document and extract chunks"""
        pass
    
    @abstractmethod
    async def chunk_document(self, content: str, chunk_size: int = 1000) -> List[DocumentChunk]:
        """Chunk document into smaller pieces"""
        pass
    
    @abstractmethod
    async def generate_embeddings(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Generate embeddings for document chunks"""
        pass

