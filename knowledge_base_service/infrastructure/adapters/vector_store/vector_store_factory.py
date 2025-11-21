"""
Vector store factory for creating swappable vector store implementations
"""
from config import get_settings
from domain.ports.vector_store_port import IVectorStore
from infrastructure.adapters.vector_store.qdrant_adapter import QdrantVectorStore

settings = get_settings()


class VectorStoreFactory:
    """Factory for creating vector store instances"""
    
    @staticmethod
    def create(collection_name: str = "travel_base") -> IVectorStore:
        """Create vector store based on configuration"""
        vector_db_type = settings.vector_db_type.lower()
        
        if vector_db_type == "qdrant":
            return QdrantVectorStore(collection_name=collection_name)
        elif vector_db_type == "weaviate":
            # TODO: Implement Weaviate adapter
            from infrastructure.adapters.vector_store.weaviate_adapter import WeaviateVectorStore
            return WeaviateVectorStore(collection_name=collection_name)
        elif vector_db_type == "chroma":
            # TODO: Implement Chroma adapter
            from infrastructure.adapters.vector_store.chroma_adapter import ChromaVectorStore
            return ChromaVectorStore(collection_name=collection_name)
        else:
            raise ValueError(f"Unsupported vector database type: {vector_db_type}")

