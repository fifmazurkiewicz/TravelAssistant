"""
Document repository adapter - retrieves documents from Qdrant vector store
"""
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from config import get_settings
from domain.entities.document import Document
from domain.ports.document_port import IDocumentRepository
from infrastructure.adapters.vector_store.vector_store_factory import VectorStoreFactory

settings = get_settings()


class DocumentRepository(IDocumentRepository):
    """Document repository implementation - retrieves from Qdrant"""
    
    def __init__(self, db: Session):
        self.db = db
        self.vector_store = VectorStoreFactory.create(collection_name=getattr(settings, 'collection_name', "travel_base"))
    
    async def create(self, document: Document) -> Document:
        """Create new document - not implemented (write operations in knowledge_management_service)"""
        raise NotImplementedError("Create operations should be performed via Knowledge Management Service")
    
    async def get_by_id(self, document_id: int) -> Optional[Document]:
        """Get document by ID from Qdrant"""
        try:
            # Scroll through all points to find document with matching document_id
            all_points = await self.vector_store.scroll_all(limit=10000, with_payload=True)
            
            # Find first point with matching document_id
            for point in all_points:
                payload = point.get("payload", {})
                if payload.get("document_id") == document_id:
                    # Extract document metadata from first chunk
                    filename = payload.get("filename", f"document_{document_id}")
                    content_type = payload.get("content_type")
                    file_size = payload.get("file_size", 0)
                    created_at_str = payload.get("created_at")
                    
                    # Parse created_at if it's a string
                    if created_at_str:
                        if isinstance(created_at_str, str):
                            try:
                                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                            except:
                                created_at = datetime.utcnow()
                        else:
                            created_at = datetime.utcnow()
                    else:
                        created_at = datetime.utcnow()
                    
                    return Document(
                        id=document_id,
                        filename=filename,
                        content_type=content_type,
                        file_size=file_size,
                        created_at=created_at
                    )
            
            return None
        except Exception as e:
            # Return None on error (document not found)
            return None
    
    async def list_all(self, skip: int = 0, limit: int = 100) -> List[Document]:
        """List all documents from Qdrant"""
        try:
            # Scroll through all points in Qdrant
            all_points = await self.vector_store.scroll_all(limit=10000, with_payload=True)
            
            # Extract unique document_ids and their metadata
            documents_dict: Dict[int, Dict] = {}
            
            for point in all_points:
                payload = point.get("payload", {})
                document_id = payload.get("document_id")
                
                if document_id is not None:
                    # Use first occurrence of document_id to get metadata
                    if document_id not in documents_dict:
                        filename = payload.get("filename", f"document_{document_id}")
                        content_type = payload.get("content_type")
                        file_size = payload.get("file_size", 0)
                        created_at_str = payload.get("created_at")
                        
                        # Parse created_at
                        if created_at_str:
                            if isinstance(created_at_str, str):
                                try:
                                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                                except:
                                    created_at = datetime.utcnow()
                            else:
                                created_at = datetime.utcnow()
                        else:
                            created_at = datetime.utcnow()
                        
                        documents_dict[document_id] = {
                            "id": document_id,
                            "filename": filename,
                            "content_type": content_type,
                            "file_size": file_size,
                            "created_at": created_at
                        }
            
            # Convert to Document entities and apply pagination
            documents = [
                Document(
                    id=doc_data["id"],
                    filename=doc_data["filename"],
                    content_type=doc_data["content_type"],
                    file_size=doc_data["file_size"],
                    created_at=doc_data["created_at"]
                )
                for doc_data in sorted(documents_dict.values(), key=lambda x: x["created_at"], reverse=True)
            ]
            
            # Apply pagination
            return documents[skip:skip + limit]
        except Exception as e:
            # Return empty list on error
            return []
    
    async def delete(self, document_id: int) -> bool:
        """Delete document - not implemented (write operations in knowledge_management_service)"""
        raise NotImplementedError("Delete operations should be performed via Knowledge Management Service")

