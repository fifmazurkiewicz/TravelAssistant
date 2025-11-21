"""
Knowledge base search endpoints
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

logger = logging.getLogger(__name__)

from app.api.v1.schemas import (
    ChatRequest,
    ChatResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from domain.ports.knowledge_base_port import IKnowledgeBaseReader
from exceptions import ExternalServiceError, ValidationError
from infrastructure.adapters.knowledge_base_adapter import KnowledgeBaseReader
from infrastructure.adapters.llm_adapter import LLMAdapter

router = APIRouter()


def get_knowledge_base_reader() -> IKnowledgeBaseReader:
    """Dependency injection for knowledge base reader"""
    return KnowledgeBaseReader()


def get_llm_adapter() -> LLMAdapter:
    """Dependency injection for LLM adapter"""
    return LLMAdapter()


@router.post("/query", response_model=SearchResponse)
async def search_knowledge_base(
    request: SearchRequest,
    top_k: int = Query(default=5, ge=1, le=20),
    search_type: str = Query(default="hybrid", regex="^(hybrid|vector|bm25)$"),
    user_id: Optional[int] = Query(default=None, description="Filter by user ID"),
    include_global: bool = Query(default=True, description="Include global documents in user search"),
    reader: IKnowledgeBaseReader = Depends(get_knowledge_base_reader)
):
    """Search knowledge base using hybrid search (BM25 + Vector)"""
    try:
        results = await reader.search(
            query=request.query,
            top_k=top_k,
            filters=request.filters,
            search_type=search_type,
            user_id=user_id,
            include_global=include_global
        )
        
        return SearchResponse(
            query=request.query,
            results=[
                SearchResult(
                    content=result.content,
                    metadata=result.metadata,
                    score=result.score
                )
                for result in results
            ],
            total_results=len(results)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ExternalServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/chat", response_model=ChatResponse)
async def chat_with_llm(
    request: ChatRequest,
    top_k: int = Query(default=5, ge=1, le=20),
    search_type: str = Query(default="hybrid", regex="^(hybrid|vector|bm25)$"),
    user_id: Optional[int] = Query(default=None, description="Filter by user ID"),
    include_global: bool = Query(default=True, description="Include global documents in user search"),
    reader: IKnowledgeBaseReader = Depends(get_knowledge_base_reader),
    llm_adapter: LLMAdapter = Depends(get_llm_adapter)
):
    """
    Chat endpoint: Search knowledge base and generate LLM response
    
    This endpoint:
    1. Searches the knowledge base for relevant documents
    2. Uses LLM to generate a natural language response based on found documents
    """
    try:
        # Step 1: Search knowledge base
        search_results = await reader.search(
            query=request.query,
            top_k=top_k,
            filters=request.filters,
            search_type=search_type,
            user_id=user_id,
            include_global=include_global
        )
        
        # Filter documents by relevance score (only include documents with score >= 0.5)
        RELEVANCE_THRESHOLD = 0.5
        filtered_results = [result for result in search_results if result.score >= RELEVANCE_THRESHOLD]
        
        # Log filtering results
        filtered_count = len(search_results) - len(filtered_results)
        if filtered_count > 0:
            logger.info(f"🔍 Filtrowanie dokumentów: {filtered_count} dokumentów z score < {RELEVANCE_THRESHOLD} zostało odrzuconych")
            logger.info(f"   Przed filtrowaniem: {len(search_results)} dokumentów")
            logger.info(f"   Po filtrowaniu: {len(filtered_results)} dokumentów (score >= {RELEVANCE_THRESHOLD})")
        else:
            logger.debug(f"✅ Wszystkie {len(search_results)} dokumentów mają score >= {RELEVANCE_THRESHOLD}")
        
        # Convert search results to format expected by LLM (only high-relevance documents)
        context_documents = [
            {
                "content": result.content,
                "metadata": result.metadata or {}
            }
            for result in filtered_results
        ]
        
        # Step 2: Generate LLM response
        conversation_history = request.conversation_history or []
        llm_response = await llm_adapter.generate_response(
            user_query=request.query,
            context_documents=context_documents,
            conversation_history=conversation_history
        )
        
        # Step 3: Return response with sources (include all results, not just filtered ones)
        return ChatResponse(
            query=request.query,
            response=llm_response,
            sources=[
                SearchResult(
                    content=result.content,
                    metadata=result.metadata,
                    score=result.score
                )
                for result in search_results
            ],
            total_sources=len(search_results)
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ExternalServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}"
        )


@router.get("/semantic-search", response_model=SearchResponse)
async def semantic_search(
    query: str = Query(..., min_length=1),
    top_k: int = Query(default=5, ge=1, le=20),
    search_type: str = Query(default="hybrid", regex="^(hybrid|vector|bm25)$"),
    user_id: Optional[int] = Query(default=None, description="Filter by user ID"),
    include_global: bool = Query(default=True, description="Include global documents in user search"),
    reader: IKnowledgeBaseReader = Depends(get_knowledge_base_reader)
):
    """Semantic search endpoint with hybrid search support"""
    try:
        results = await reader.search(
            query=query,
            top_k=top_k,
            search_type=search_type,
            user_id=user_id,
            include_global=include_global
        )
        
        return SearchResponse(
            query=query,
            results=[
                SearchResult(
                    content=result.content,
                    metadata=result.metadata,
                    score=result.score
                )
                for result in results
            ],
            total_results=len(results)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ExternalServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )

