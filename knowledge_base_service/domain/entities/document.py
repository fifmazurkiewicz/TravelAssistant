"""
Document entity (DDD Aggregate Root)
"""
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field


@dataclass
class Document:
    """Document aggregate root"""
    id: Optional[int] = None
    filename: str = ""
    content_type: Optional[str] = None
    file_size: int = 0
    file_path: Optional[str] = None
    content: Optional[str] = None
    chunks: List['DocumentChunk'] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    def add_chunk(self, chunk: 'DocumentChunk'):
        """Add chunk to document"""
        self.chunks.append(chunk)
        self.updated_at = datetime.utcnow()


@dataclass
class DocumentChunk:
    """Document chunk value object"""
    id: Optional[int] = None
    document_id: int = 0
    content: str = ""
    chunk_index: int = 0
    metadata: dict = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    # User and scope information
    user_id: Optional[int] = None  # None = global document, int = user document
    is_global: bool = True  # True = global, False = user-specific

