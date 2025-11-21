"""
Configuration for Knowledge Base Service
"""
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_service_root() -> Path:
    """Find project root directory (main folder, not service folder) by looking for .env file or main pyproject.toml"""
    current = Path(__file__).resolve()
    
    # Start from current file and go up to find the main project root
    # We want the TravelAssistant root, not knowledge_base_service folder
    for parent in current.parents:
        # Check if .env exists (most reliable indicator of project root)
        if (parent / ".env").exists():
            return parent
        
        # Check for main pyproject.toml (not the one in service folders)
        # Main project root should have service directories as siblings
        if (parent / "pyproject.toml").exists():
            # Verify this is the main project root by checking for service directories
            # Main root should have user_service, knowledge_base_service, etc. as siblings
            if (parent / "user_service").exists() or (parent / "knowledge_base_service").exists():
                # This is the main project root
                return parent
    
    # Fallback to current working directory
    return Path.cwd()


# Find service root and .env file path
SERVICE_ROOT = _find_service_root()
ENV_FILE_PATH = SERVICE_ROOT / ".env"


class Settings(BaseSettings):
    """Settings class for Knowledge Base Service"""
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH) if ENV_FILE_PATH.exists() else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        # Also read from environment variables (fallback)
        env_ignore_empty=True
    )
    
    # Database
    database_url: str
    database_schema: str = "knowledge_base"  # PostgreSQL schema name for this service
    
    # Application
    environment: str = "development"
    debug: bool = True
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    knowledge_base_service_port: int = Field(
        default=8002,
        description="Port aplikacji Knowledge Base Service"
    )
    knowledge_base_service_host: str = Field(
        default="0.0.0.0",
        description="Host aplikacji Knowledge Base Service"
    )
    
    @property
    def port(self) -> int:
        """Alias dla knowledge_base_service_port"""
        return self.knowledge_base_service_port
    
    @property
    def host(self) -> str:
        """Alias dla knowledge_base_service_host"""
        return self.knowledge_base_service_host
    
    # OpenRouter (optional)
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "google/gemini-2.5-flash-lite-preview-09-2025"  # Gemini 2.5 Flash Lite
    
    # Vector DB
    vector_db_type: str = "qdrant"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    weaviate_url: str = "http://localhost:8080"
    weaviate_api_key: Optional[str] = None
    chroma_persist_dir: str = "./chroma_db"
    collection_name: str = "travel_base"  # Qdrant collection name for documents
    
    # Embedding
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # Polish support
    embedding_provider: str = "sentence-transformers"
    
    # Hybrid Search
    use_hybrid_search: bool = True  # Enable BM25 + Vector hybrid search
    use_qdrant_native_bm25: bool = True  # Use Qdrant native BM25 (sparse vectors) instead of custom implementation
    hybrid_alpha: float = 0.5  # Not used with Qdrant native (Qdrant handles combination automatically)
    
    # Reranking
    reranker_enabled: bool = Field(
        default=True,
        description="Enable reranking of search results (domyślnie włączony)"
    )
    reranker_model: str = Field(
        default="sdadas/polish-reranker-roberta-v3",
        description="Model rerankingu do użycia"
    )
    reranker_score_threshold: float = Field(
        default=0.0,
        description="Próg score dla rerankingu - dokumenty poniżej tego progu będą odrzucone"
    )
    reranker_max_length: int = Field(
        default=512,
        description="Maksymalna długość kontekstu dla rerankingu (tokeny)"
    )
    reranker_batch_size: int = Field(
        default=4,
        description="Rozmiar batcha dla rerankingu (mniejsze dla GTX 1050 Ti)"
    )
    
    # File Storage
    file_storage_path: str = "./storage"
    max_file_size_mb: int = 50
    
    # Memory (shared with knowledge_management_service)
    memory_database_schema: str = "memory"  # PostgreSQL schema name for memory tables
    memory_vector_collection: str = "user_memories"  # Qdrant collection name for semantic memories


def get_settings() -> Settings:
    """Get application settings"""
    try:
        return Settings()
    except Exception as e:
        if not ENV_FILE_PATH.exists():
            raise RuntimeError(
                f"❌ Plik .env nie został znaleziony w: {ENV_FILE_PATH}\n"
                f"   Utwórz plik .env w katalogu {SERVICE_ROOT} na podstawie .env.example"
            ) from e
        raise RuntimeError(
            f"❌ Błąd podczas ładowania konfiguracji z {ENV_FILE_PATH}:\n"
            f"   {str(e)}\n"
            f"   Sprawdź, czy wszystkie wymagane zmienne są ustawione (DATABASE_URL, SECRET_KEY)\n"
            f"   Format: DATABASE_URL=postgresql://... (bez spacji wokół =)"
        ) from e

