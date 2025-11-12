"""
Configuration for Data Ingestion Service
"""
from pathlib import Path
from typing import Optional, List

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_service_root() -> Path:
    """Find service root directory by looking for .env file or pyproject.toml"""
    current = Path(__file__).resolve()
    
    # Start from current file and go up
    for parent in current.parents:
        # Check if .env exists (most reliable indicator)
        if (parent / ".env").exists():
            return parent
        # Fallback: check for pyproject.toml
        if (parent / "pyproject.toml").exists():
            return parent
    
    # Fallback to current working directory
    return Path.cwd()


# Find service root and .env file path
SERVICE_ROOT = _find_service_root()
ENV_FILE_PATH = SERVICE_ROOT / ".env"


class Settings(BaseSettings):
    """Settings class for Data Ingestion Service"""
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH) if ENV_FILE_PATH.exists() else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_ignore_empty=True
    )
    
    # Application
    environment: str = "development"
    debug: bool = True
    
    # Output directory
    output_dir: str = "./data_ingestion_output"
    
    # Wikivoyage settings
    wikivoyage_language: str = "en"
    wikivoyage_max_depth: int = 1  # How many levels deep to fetch: 1 = country -> cities, 2 = country -> cities -> attractions
    wikivoyage_level_1_sections: str = "Cities,Cities and towns"  # Comma-separated sections for level 1 (e.g., "Cities,Cities and towns")
    wikivoyage_level_2_sections: str = "See,Do"  # Comma-separated sections for level 2 (e.g., "See,Do")
    
    @property
    def wikivoyage_level_1_sections_list(self) -> List[str]:
        """Parse comma-separated level 1 sections into a list"""
        return [s.strip() for s in self.wikivoyage_level_1_sections.split(",") if s.strip()]
    
    @property
    def wikivoyage_level_2_sections_list(self) -> List[str]:
        """Parse comma-separated level 2 sections into a list"""
        return [s.strip() for s in self.wikivoyage_level_2_sections.split(",") if s.strip()]
    
    # Knowledge Base Service URL (for adding ingested data to KB)
    knowledge_base_service_url: str = "http://localhost:8002"
    
    # OpenRouter (for LLM analysis)
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "openrouter/anthropic/claude-3-haiku"  # Fast and cost-effective


def get_settings() -> Settings:
    """Get application settings"""
    try:
        return Settings()
    except Exception as e:
        if not ENV_FILE_PATH.exists():
            raise RuntimeError(
                f"❌ Plik .env nie został znaleziony w: {ENV_FILE_PATH}\n"
                f"   Utwórz plik .env w katalogu {SERVICE_ROOT}"
            ) from e
        raise RuntimeError(
            f"❌ Błąd podczas ładowania konfiguracji z {ENV_FILE_PATH}:\n"
            f"   {str(e)}"
        ) from e

