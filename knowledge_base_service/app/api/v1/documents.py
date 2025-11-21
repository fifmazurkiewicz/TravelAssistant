"""
Document metadata endpoints - Read operations only
Note: Write operations (upload, delete, update) are handled by Knowledge Management Service
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.schemas import DocumentResponse
from domain.ports.document_port import IDocumentRepository
from infrastructure.adapters.document_repository_adapter import DocumentRepository
from infrastructure.database.session import get_db

router = APIRouter()


def get_document_repository() -> IDocumentRepository:
    """Dependency injection for document repository"""
    db = next(get_db())
    return DocumentRepository(db)


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    document_repo: IDocumentRepository = Depends(get_document_repository)
):
    """List all documents"""
    documents = await document_repo.list_all(skip=skip, limit=limit)
    return [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            content_type=doc.content_type,
            file_size=doc.file_size,
            created_at=doc.created_at
        )
        for doc in documents
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    document_repo: IDocumentRepository = Depends(get_document_repository)
):
    """Get document by ID"""
    document = await document_repo.get_by_id(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        content_type=document.content_type,
        file_size=document.file_size,
        created_at=document.created_at
    )


# Note: DELETE endpoint removed - use Knowledge Management Service for write operations
# DELETE operations should be performed via: DELETE http://localhost:8007/api/v1/documents/{document_id}

