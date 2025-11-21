"""
Knowledge base reader adapter with hybrid search (BM25 + Vector)
"""
from typing import Any, Dict, List, Optional

from config import get_settings
from domain.entities.search_result import SearchResult
from domain.ports.knowledge_base_port import IKnowledgeBaseReader
from domain.ports.vector_store_port import IVectorStore
from exceptions import ExternalServiceError, ValidationError
from infrastructure.adapters.embedding_adapter import EmbeddingService
from infrastructure.adapters.reranker_adapter import RerankerService
from infrastructure.adapters.vector_store.vector_store_factory import VectorStoreFactory

settings = get_settings()


class KnowledgeBaseReader(IKnowledgeBaseReader):
    """Knowledge base reader implementation with hybrid search"""
    
    def __init__(self):
        self.vector_store: IVectorStore = VectorStoreFactory.create()
        self.embedding_service = EmbeddingService()
        self.reranker_service = RerankerService()
        self.use_hybrid_search = getattr(settings, 'use_hybrid_search', True)
    
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
        if not query or not query.strip():
            raise ValidationError("Query cannot be empty")
        
        if top_k < 1 or top_k > 100:
            raise ValidationError("top_k must be between 1 and 100")
        
        # Build search filters
        search_filters = filters or {}
        if user_id is not None:
            search_filters["user_id"] = user_id
            search_filters["include_global"] = include_global
        elif not include_global:
            # Only global documents
            search_filters["is_global"] = True
        
        # Determine search type
        if search_type is None:
            search_type = "hybrid" if self.use_hybrid_search else "vector"
        
        try:
            if search_type == "hybrid":
                return await self._hybrid_search(query.strip(), top_k, search_filters)
            elif search_type == "bm25":
                return await self._bm25_search(query.strip(), top_k, search_filters)
            else:  # vector
                return await self._vector_search(query.strip(), top_k, search_filters)
        except ExternalServiceError:
            raise
        except Exception as e:
            raise ExternalServiceError(f"Search failed: {str(e)}")
    
    async def _vector_search(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[SearchResult]:
        """Vector-only search"""
        # Get more results initially if reranking is enabled
        initial_top_k = top_k * 2 if self.reranker_service.is_enabled() else top_k
        
        query_embedding = await self.embedding_service.embed_text(query)
        results = await self.vector_store.search(
            query_embedding=query_embedding,
            top_k=initial_top_k,
            filters=filters,
            use_hybrid=False  # Vector only
        )
        
        # Convert to SearchResult list
        search_results = [
            SearchResult(
                content=result["content"],
                metadata=result.get("metadata"),
                score=result.get("score", 0.0)
            )
            for result in results
        ]
        
        # Apply reranking if enabled
        if self.reranker_service.is_enabled() and search_results:
            documents = [result.content for result in search_results]
            initial_scores = [result.score for result in search_results]
            
            # Rerank documents
            reranked = await self.reranker_service.rerank(
                query=query,
                documents=documents,
                scores=initial_scores
            )
            
            # Create new SearchResult list with reranked scores
            reranked_results = []
            for doc_content, reranked_score in reranked:
                original_result = next(
                    (r for r in search_results if r.content == doc_content),
                    None
                )
                if original_result:
                    reranked_results.append(
                        SearchResult(
                            content=doc_content,
                            metadata=original_result.metadata,
                            score=reranked_score
                        )
                    )
            
            return reranked_results[:top_k]
        
        return search_results[:top_k]
    
    async def _bm25_search(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """BM25-only search using Qdrant sparse vectors"""
        # Get more results initially if reranking is enabled
        initial_top_k = top_k * 2 if self.reranker_service.is_enabled() else top_k
        
        # Use Qdrant sparse vector search (BM25 only)
        # Generate empty embedding for BM25-only search
        empty_embedding = [0.0] * 384  # Dummy embedding, won't be used
        
        results = await self.vector_store.search(
            query_embedding=empty_embedding,
            top_k=initial_top_k,
            filters=filters,
            query_text=query,  # For BM25 sparse vector
            use_hybrid=False  # BM25 only (sparse vector)
        )
        
        # Note: For pure BM25, we'd need to use sparse-only search
        # This is a workaround - Qdrant will use sparse vector
        # TODO: Implement pure sparse vector search when Qdrant API supports it
        
        # Convert to SearchResult list
        search_results = [
            SearchResult(
                content=result["content"],
                metadata=result.get("metadata"),
                score=result.get("score", 0.0)
            )
            for result in results
        ]
        
        # Apply reranking if enabled
        if self.reranker_service.is_enabled() and search_results:
            documents = [result.content for result in search_results]
            initial_scores = [result.score for result in search_results]
            
            # Rerank documents
            reranked = await self.reranker_service.rerank(
                query=query,
                documents=documents,
                scores=initial_scores
            )
            
            # Create new SearchResult list with reranked scores
            reranked_results = []
            for doc_content, reranked_score in reranked:
                original_result = next(
                    (r for r in search_results if r.content == doc_content),
                    None
                )
                if original_result:
                    reranked_results.append(
                        SearchResult(
                            content=doc_content,
                            metadata=original_result.metadata,
                            score=reranked_score
                        )
                    )
            
            return reranked_results[:top_k]
        
        return search_results[:top_k]
    
    async def _hybrid_search(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[SearchResult]:
        """Hybrid search using Qdrant native hybrid search (dense + sparse BM25)"""
        # Use Qdrant native hybrid search - combines dense (embedding) + sparse (BM25)
        # Get more results initially if reranking is enabled (reranking will filter)
        initial_top_k = top_k * 2 if self.reranker_service.is_enabled() else top_k
        
        query_embedding = await self.embedding_service.embed_text(query)
        results = await self.vector_store.search(
            query_embedding=query_embedding,
            top_k=initial_top_k,
            filters=filters,
            query_text=query,  # For BM25 sparse vector generation
            use_hybrid=True  # Use native Qdrant hybrid search
        )
        
        # Convert to SearchResult list
        search_results = [
            SearchResult(
                content=result["content"],
                metadata=result.get("metadata"),
                score=result.get("score", 0.0)
            )
            for result in results
        ]
        
        # Apply reranking if enabled
        if self.reranker_service.is_enabled() and search_results:
            documents = [result.content for result in search_results]
            initial_scores = [result.score for result in search_results]
            
            # Rerank documents
            reranked = await self.reranker_service.rerank(
                query=query,
                documents=documents,
                scores=initial_scores
            )
            
            # Create new SearchResult list with reranked scores
            # Map back metadata from original results
            reranked_results = []
            for doc_content, reranked_score in reranked:
                # Find original result to preserve metadata
                original_result = next(
                    (r for r in search_results if r.content == doc_content),
                    None
                )
                if original_result:
                    reranked_results.append(
                        SearchResult(
                            content=doc_content,
                            metadata=original_result.metadata,
                            score=reranked_score
                        )
                    )
            
            # Return top_k after reranking
            return reranked_results[:top_k]
        
        return search_results[:top_k]
    
    # Note: Write operations (add_document_chunks, delete_document) removed
    # Use Knowledge Management Service for write operations
    # This class now only handles read operations (search)

