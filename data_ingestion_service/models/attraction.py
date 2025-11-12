"""
Attraction information model
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Attraction(BaseModel):
    """Standardized attraction information"""
    
    name: str = Field(..., description="Nazwa atrakcji")
    location: str = Field(..., description="Lokalizacja (miasto, kraj)")
    country: Optional[str] = Field(None, description="Kraj")
    city: Optional[str] = Field(None, description="Miasto")
    description: str = Field(..., description="Opis atrakcji")
    category: Optional[str] = Field(None, description="Kategoria (np. muzeum, zabytek, park)")
    coordinates: Optional[dict] = Field(None, description="Współrzędne geograficzne (lat, lon)")
    opening_hours: Optional[str] = Field(None, description="Godziny otwarcia")
    price_info: Optional[str] = Field(None, description="Informacje o cenach")
    rating: Optional[float] = Field(None, description="Ocena (0-5)")
    review_count: Optional[int] = Field(None, description="Liczba opinii")
    tips: List[str] = Field(default_factory=list, description="Praktyczne wskazówki")
    best_time_to_visit: Optional[str] = Field(None, description="Najlepszy czas na wizytę")
    source: str = Field(..., description="Źródło danych")
    source_url: Optional[str] = Field(None, description="URL źródła")
    fetched_at: datetime = Field(default_factory=datetime.utcnow, description="Data pobrania")
    metadata: dict = Field(default_factory=dict, description="Dodatkowe metadane")

