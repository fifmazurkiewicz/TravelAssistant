"""
Data standardizer for converting raw data to standardized models
"""
from typing import Any, Dict, List

from models.attraction import Attraction
from models.country_info import CountryInfo
from models.hotel_offer import HotelOffer
from models.restaurant_info import RestaurantInfo
from processors.text_cleaner import TextCleaner


class DataStandardizer:
    """Standardize raw data from fetchers to Pydantic models"""
    
    def __init__(self):
        self.text_cleaner = TextCleaner()
    
    def standardize_country_info(self, raw_data: List[Dict[str, Any]]) -> List[CountryInfo]:
        """Convert raw country data to CountryInfo models"""
        standardized = []
        
        for data in raw_data:
            try:
                country_info = CountryInfo(
                    name=data.get("name", ""),
                    code=data.get("code"),
                    capital=data.get("capital"),
                    population=data.get("population"),
                    area_km2=data.get("area_km2"),
                    currency=data.get("currency"),
                    languages=data.get("languages", []),
                    timezone=data.get("timezone"),
                    description=self.text_cleaner.clean_text(data.get("description")),
                    history=self.text_cleaner.clean_text(data.get("history")),
                    culture=self.text_cleaner.clean_text(data.get("culture")),
                    practical_info=self.text_cleaner.clean_text(data.get("practical_info")),
                    coordinates=data.get("coordinates"),
                    source=data.get("source", "unknown"),
                    source_url=data.get("source_url"),
                    metadata=data.get("metadata", {})
                )
                standardized.append(country_info)
            except Exception as e:
                print(f"Error standardizing country info: {e}")
                continue
        
        return standardized
    
    def standardize_attractions(self, raw_data: List[Dict[str, Any]]) -> List[Attraction]:
        """Convert raw attraction data to Attraction models"""
        standardized = []
        
        for data in raw_data:
            try:
                attraction = Attraction(
                    name=data.get("name", ""),
                    location=data.get("location", ""),
                    country=data.get("country"),
                    city=data.get("city"),
                    description=self.text_cleaner.clean_text(data.get("description", "")),
                    category=data.get("category"),
                    coordinates=data.get("coordinates"),
                    opening_hours=data.get("opening_hours"),
                    price_info=data.get("price_info"),
                    rating=data.get("rating"),
                    review_count=data.get("review_count"),
                    tips=data.get("tips", []),
                    best_time_to_visit=data.get("best_time_to_visit"),
                    source=data.get("source", "unknown"),
                    source_url=data.get("source_url"),
                    metadata=data.get("metadata", {})
                )
                standardized.append(attraction)
            except Exception as e:
                print(f"Error standardizing attraction: {e}")
                continue
        
        return standardized
    
    def standardize_hotels(self, raw_data: List[Dict[str, Any]]) -> List[HotelOffer]:
        """Convert raw hotel data to HotelOffer models"""
        standardized = []
        
        for data in raw_data:
            try:
                hotel = HotelOffer(
                    name=data.get("name", ""),
                    location=data.get("location", ""),
                    city=data.get("city"),
                    country=data.get("country"),
                    address=data.get("address"),
                    coordinates=data.get("coordinates"),
                    description=self.text_cleaner.clean_text(data.get("description")),
                    rating=data.get("rating"),
                    review_count=data.get("review_count"),
                    price_range=data.get("price_range"),
                    amenities=data.get("amenities", []),
                    room_types=data.get("room_types", []),
                    source=data.get("source", "unknown"),
                    source_url=data.get("source_url"),
                    metadata=data.get("metadata", {})
                )
                standardized.append(hotel)
            except Exception as e:
                print(f"Error standardizing hotel: {e}")
                continue
        
        return standardized
    
    def standardize_restaurants(self, raw_data: List[Dict[str, Any]]) -> List[RestaurantInfo]:
        """Convert raw restaurant data to RestaurantInfo models"""
        standardized = []
        
        for data in raw_data:
            try:
                restaurant = RestaurantInfo(
                    name=data.get("name", ""),
                    location=data.get("location", ""),
                    city=data.get("city"),
                    country=data.get("country"),
                    address=data.get("address"),
                    coordinates=data.get("coordinates"),
                    description=self.text_cleaner.clean_text(data.get("description")),
                    cuisine_type=data.get("cuisine_type"),
                    price_range=data.get("price_range"),
                    rating=data.get("rating"),
                    review_count=data.get("review_count"),
                    opening_hours=data.get("opening_hours"),
                    specialties=data.get("specialties", []),
                    source=data.get("source", "unknown"),
                    source_url=data.get("source_url"),
                    metadata=data.get("metadata", {})
                )
                standardized.append(restaurant)
            except Exception as e:
                print(f"Error standardizing restaurant: {e}")
                continue
        
        return standardized

