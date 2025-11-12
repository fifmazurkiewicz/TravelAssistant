"""
Country information model
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CountryInfo(BaseModel):
    """Standardized country information"""
    
    name: str = Field(..., description="Nazwa kraju")
    code: Optional[str] = Field(None, description="Kod kraju (ISO 3166-1 alpha-2)")
    capital: Optional[str] = Field(None, description="Stolica")
    population: Optional[int] = Field(None, description="Populacja")
    area_km2: Optional[float] = Field(None, description="Powierzchnia w km²")
    currency: Optional[str] = Field(None, description="Waluta")
    languages: List[str] = Field(default_factory=list, description="Języki urzędowe")
    timezone: Optional[str] = Field(None, description="Strefa czasowa")
    description: Optional[str] = Field(None, description="Opis kraju")
    history: Optional[str] = Field(None, description="Historia")
    culture: Optional[str] = Field(None, description="Kultura")
    practical_info: Optional[str] = Field(None, description="Informacje praktyczne")
    coordinates: Optional[dict] = Field(None, description="Współrzędne geograficzne (lat, lon)")
    source: str = Field(..., description="Źródło danych")
    source_url: Optional[str] = Field(None, description="URL źródła")
    fetched_at: datetime = Field(default_factory=datetime.utcnow, description="Data pobrania")
    metadata: dict = Field(default_factory=dict, description="Dodatkowe metadane")

