"""
Restaurant information model
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RestaurantInfo(BaseModel):
    """Standardized restaurant information"""
    
    name: str = Field(..., description="Nazwa restauracji")
    location: str = Field(..., description="Lokalizacja")
    city: Optional[str] = Field(None, description="Miasto")
    country: Optional[str] = Field(None, description="Kraj")
    address: Optional[str] = Field(None, description="Adres")
    coordinates: Optional[dict] = Field(None, description="Współrzędne geograficzne (lat, lon)")
    description: Optional[str] = Field(None, description="Opis restauracji")
    cuisine_type: Optional[str] = Field(None, description="Typ kuchni")
    price_range: Optional[str] = Field(None, description="Zakres cenowy")
    rating: Optional[float] = Field(None, description="Ocena (0-5)")
    review_count: Optional[int] = Field(None, description="Liczba opinii")
    opening_hours: Optional[str] = Field(None, description="Godziny otwarcia")
    specialties: List[str] = Field(default_factory=list, description="Specjalności")
    source: str = Field(..., description="Źródło danych")
    source_url: Optional[str] = Field(None, description="URL źródła")
    fetched_at: datetime = Field(default_factory=datetime.utcnow, description="Data pobrania")
    metadata: dict = Field(default_factory=dict, description="Dodatkowe metadane")

