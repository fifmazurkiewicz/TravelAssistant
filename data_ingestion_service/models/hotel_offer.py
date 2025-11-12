"""
Hotel offer information model
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class HotelOffer(BaseModel):
    """Standardized hotel offer information"""
    
    name: str = Field(..., description="Nazwa hotelu")
    location: str = Field(..., description="Lokalizacja")
    city: Optional[str] = Field(None, description="Miasto")
    country: Optional[str] = Field(None, description="Kraj")
    address: Optional[str] = Field(None, description="Adres")
    coordinates: Optional[dict] = Field(None, description="Współrzędne geograficzne (lat, lon)")
    description: Optional[str] = Field(None, description="Opis hotelu")
    rating: Optional[float] = Field(None, description="Ocena (0-5)")
    review_count: Optional[int] = Field(None, description="Liczba opinii")
    price_range: Optional[str] = Field(None, description="Zakres cenowy")
    amenities: List[str] = Field(default_factory=list, description="Udogodnienia")
    room_types: List[str] = Field(default_factory=list, description="Typy pokoi")
    source: str = Field(..., description="Źródło danych")
    source_url: Optional[str] = Field(None, description="URL źródła")
    fetched_at: datetime = Field(default_factory=datetime.utcnow, description="Data pobrania")
    metadata: dict = Field(default_factory=dict, description="Dodatkowe metadane")

