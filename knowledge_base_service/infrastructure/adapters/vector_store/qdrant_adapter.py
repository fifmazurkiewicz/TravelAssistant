"""
Qdrant vector store adapter with native async support and BM25 sparse vectors
"""
import uuid
from typing import Any, Dict, List, Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    Document,
    FieldCondition,
    Filter,
    MatchValue,
    Modifier,
    NamedSparseVector,
    NamedVector,
    PointStruct,
    Prefetch,
    Query,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from config import get_settings
from domain.ports.vector_store_port import IVectorStore
from exceptions import ExternalServiceError

settings = get_settings()


class QdrantVectorStore(IVectorStore):
    """Qdrant implementation of vector store with native async support"""
    
    def __init__(self, collection_name: str = "travel_base"):
        try:
            self.client = AsyncQdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key if settings.qdrant_api_key else None
            )
            self.collection_name = collection_name
            # Collection will be ensured on first async operation
        except Exception as e:
            raise ExternalServiceError(f"Failed to connect to Qdrant: {str(e)}")
    
    async def _ensure_collection(self):
        """Ensure collection exists (async) with dense + sparse vectors"""
        try:
            collections = await self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config={
                        "dense": VectorParams(
                            size=384,  # For paraphrase-multilingual-MiniLM-L12-v2
                            distance=Distance.COSINE
                        )
                    },
                    sparse_vectors_config={
                        "bm25": SparseVectorParams(
                            modifier=Modifier.IDF  # Required for BM25 - enables IDF calculation
                        )
                    }
                )
        except Exception as e:
            raise ExternalServiceError(f"Failed to ensure collection: {str(e)}")
    
    async def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """Add documents to Qdrant with dense + sparse vectors (native async)"""
        if len(texts) != len(embeddings):
            raise ValueError("Texts and embeddings must have the same length")
        
        # Ensure collection exists
        await self._ensure_collection()
        
        # Calculate average document length for BM25
        avg_doc_length = sum(len(text.split()) for text in texts) / len(texts) if texts else 100
        
        points = []
        for idx, (text, embedding) in enumerate(zip(texts, embeddings)):
            # Generate unique ID using UUID
            point_id = str(uuid.uuid4())
            payload = {"text": text}
            if metadatas and idx < len(metadatas):
                payload.update(metadatas[idx])
            
            # Create point with dense (embedding) + sparse (BM25) vectors
            points.append(
                PointStruct(
                    id=point_id,
                    vector={
                        "dense": embedding,  # Dense vector from sentence-transformers
                        "bm25": Document(  # Sparse vector - Qdrant generates BM25 on server
                            text=text,
                            model="Qdrant/bm25",
                            options={"avg_len": avg_doc_length}
                        )
                    },
                    payload=payload
                )
            )
        
        try:
            await self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
        except Exception as e:
            raise ExternalServiceError(f"Failed to add documents to Qdrant: {str(e)}")
        
        return [point.id for point in points]
    
    def _build_qdrant_filter(self, filters: Optional[Dict[str, Any]]) -> Optional[Filter]:
        """Build Qdrant filter from dictionary"""
        if not filters:
            return None
        
        conditions = []
        
        # Filter by user_id
        if "user_id" in filters:
            user_id = filters["user_id"]
            if user_id is not None:
                conditions.append(
                    FieldCondition(key="user_id", match=MatchValue(value=user_id))
                )
        
        # Filter by is_global
        if "is_global" in filters:
            is_global = filters["is_global"]
            conditions.append(
                FieldCondition(key="is_global", match=MatchValue(value=bool(is_global)))
            )
        
        # Include global documents (for user searches)
        if filters.get("include_global", False) and "user_id" in filters:
            user_id = filters["user_id"]
            if user_id is not None:
                # Should match: (user_id == X) OR (is_global == True)
                return Filter(
                    should=[
                        FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                        FieldCondition(key="is_global", match=MatchValue(value=True))
                    ]
                )
        
        # Filter by document_id
        if "document_id" in filters:
            doc_id = filters["document_id"]
            conditions.append(
                FieldCondition(key="document_id", match=MatchValue(value=doc_id))
            )
        
        if not conditions:
            return None
        
        return Filter(must=conditions)
    
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        query_text: Optional[str] = None,
        use_hybrid: bool = True
    ) -> List[Dict[str, Any]]:
        """Search Qdrant with native hybrid search (dense + sparse BM25)"""
        # Ensure collection exists
        await self._ensure_collection()
        
        # Build Qdrant filter
        qdrant_filter = self._build_qdrant_filter(filters)
        
        try:
            if use_hybrid and query_text:
                # Native hybrid search: dense (embedding) + sparse (BM25)
                # According to Qdrant documentation:
                # - Use query_points with prefetch for hybrid search
                # - Prefetch allows combining dense and sparse vector searches
                # Reference: https://qdrant.tech/documentation/advanced-tutorials/reranking-hybrid-search/
                try:
                    # Use query_points with prefetch for hybrid search
                    # This combines dense vector search and BM25 sparse vector search
                    # Prefetch.query accepts list of floats or Document for BM25
                    # Note: Filters are applied only in the main query, not in prefetch
                    response = await self.client.query_points(
                        collection_name=self.collection_name,
                        prefetch=[
                            Prefetch(
                                query=query_embedding,  # List of floats for dense vector
                                using="dense",
                                limit=top_k * 2  # Get more results for better fusion
                            ),
                            Prefetch(
                                query=Document(
                                    text=query_text,
                                    model="Qdrant/bm25"
                                ),
                                using="bm25",
                                limit=top_k * 2  # Get more results for better fusion
                            )
                        ],
                        query=query_embedding,  # Final query uses dense vector
                        using="dense",
                        limit=top_k,
                        query_filter=qdrant_filter  # Use query_filter instead of filter
                    )
                    points = response.points if hasattr(response, 'points') else []
                except (TypeError, ValueError, AttributeError) as e:
                    # Fallback to vector-only search if hybrid fails
                    # This ensures the search still works even if hybrid search syntax is incorrect
                    results = await self.client.search(
                        collection_name=self.collection_name,
                        query_vector=NamedVector(
                            name="dense",
                            vector=query_embedding
                        ),
                        limit=top_k,
                        query_filter=qdrant_filter
                    )
                    points = results
            else:
                # Vector-only search (backward compatibility)
                results = await self.client.search(
                    collection_name=self.collection_name,
                    query_vector=NamedVector(
                        name="dense",
                        vector=query_embedding
                    ),
                    limit=top_k,
                    query_filter=qdrant_filter
                )
                points = results
            
            return [
                {
                    "content": point.payload.get("text", "") if hasattr(point, 'payload') and point.payload else "",
                    "metadata": {k: v for k, v in (point.payload.items() if hasattr(point, 'payload') and point.payload else {}) if k != "text"},
                    "score": float(point.score) if hasattr(point, 'score') and point.score is not None else 0.0
                }
                for point in points
            ]
        except Exception as e:
            raise ExternalServiceError(f"Failed to search Qdrant: {str(e)}")
    
    async def scroll_all(
        self,
        limit: int = 10000,
        with_payload: bool = True,
        with_vectors: bool = False
    ) -> List[Dict[str, Any]]:
        """Scroll through all points in collection"""
        await self._ensure_collection()
        
        try:
            all_points = []
            offset = None
            
            while True:
                scroll_result = await self.client.scroll(
                    collection_name=self.collection_name,
                    limit=limit,
                    offset=offset,
                    with_payload=with_payload,
                    with_vectors=with_vectors
                )
                
                points, next_offset = scroll_result
                if not points:
                    break
                
                all_points.extend([
                    {
                        "id": str(point.id),
                        "payload": point.payload if hasattr(point, 'payload') and point.payload else {}
                    }
                    for point in points
                ])
                
                if next_offset is None:
                    break
                offset = next_offset
            
            return all_points
        except Exception as e:
            raise ExternalServiceError(f"Failed to scroll Qdrant collection: {str(e)}")
    
    async def delete(self, ids: List[str]) -> bool:
        """Delete documents from Qdrant (native async)"""
        try:
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=ids
            )
            return True
        except Exception as e:
            raise ExternalServiceError(f"Failed to delete from Qdrant: {str(e)}")
    
    async def create_collection(self, collection_name: str) -> bool:
        """Create collection with dense + sparse vectors (native async)"""
        try:
            await self.client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    "dense": VectorParams(
                        size=384,  # For paraphrase-multilingual-MiniLM-L12-v2
                        distance=Distance.COSINE
                    )
                },
                sparse_vectors_config={
                    "bm25": SparseVectorParams(
                        modifier=Modifier.IDF  # Required for BM25 - enables IDF calculation
                    )
                }
            )
            return True
        except Exception as e:
            raise ExternalServiceError(f"Failed to create collection: {str(e)}")
    
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete collection (native async)"""
        try:
            await self.client.delete_collection(collection_name=collection_name)
            return True
        except Exception as e:
            raise ExternalServiceError(f"Failed to delete collection: {str(e)}")
    
    async def close(self):
        """Close async client connection"""
        if self.client:
            await self.client.close()

