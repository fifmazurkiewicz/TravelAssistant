"""
TripAdvisor fetcher using web scraping
"""
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from .base_fetcher import BaseFetcher


class TripAdvisorFetcher(BaseFetcher):
    """Fetcher for TripAdvisor data using web scraping"""
    
    BASE_URL = "https://www.tripadvisor.com"
    
    @property
    def source_name(self) -> str:
        return "tripadvisor"
    
    async def fetch_country_info(self, country_name: str) -> List[Dict[str, Any]]:
        """Fetch country information from TripAdvisor"""
        # TripAdvisor doesn't have general country info, return empty
        return []
    
    async def fetch_attractions(self, location: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch attractions from TripAdvisor"""
        results = []
        
        # Note: TripAdvisor requires JavaScript rendering, so this is a placeholder
        # In production, would need Selenium or Playwright for dynamic content
        
        search_url = f"{self.BASE_URL}/Search?q={location.replace(' ', '+')}"
        response = await self._make_request(search_url)
        
        if response:
            # Parse HTML using BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract attraction data from HTML
            # Note: TripAdvisor uses JavaScript heavily, so this may not work for all content
            # For full functionality, would need Selenium or Playwright
            
            # Try to find attraction listings
            attraction_elements = soup.find_all(['div', 'article'], class_=lambda x: bool(x and ('attraction' in x.lower() or 'listing' in x.lower())))
            
            for element in attraction_elements[:limit]:
                name_elem = element.find(['h2', 'h3', 'a'], class_=lambda x: bool(x and 'name' in x.lower()))
                name = name_elem.get_text(strip=True) if name_elem else f"Attraction in {location}"
                
                rating_elem = element.find(class_=lambda x: bool(x and 'rating' in x.lower()))
                rating = None
                if rating_elem:
                    rating_text = rating_elem.get_text(strip=True)
                    # Try to extract numeric rating
                    try:
                        rating = float(rating_text.split()[0])
                    except (ValueError, IndexError):
                        pass
                
                description_elem = element.find(['p', 'div'], class_=lambda x: bool(x and ('description' in x.lower() or 'text' in x.lower())))
                description = description_elem.get_text(strip=True) if description_elem else ""
                
                attraction_data = {
                    "name": name,
                    "location": location,
                    "description": description or "Data from TripAdvisor",
                    "rating": rating,
                    "source_url": search_url,
                }
                results.append(self._add_source_metadata(attraction_data))
            
            # If no structured data found, return basic info
            if not results:
                attraction_data = {
                    "name": f"Attraction in {location}",
                    "location": location,
                    "description": "Data from TripAdvisor (may require JavaScript rendering)",
                    "source_url": search_url,
                }
                results.append(self._add_source_metadata(attraction_data))
        
        return results
    
    async def fetch_hotels(self, location: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch hotels from TripAdvisor"""
        results = []
        
        # TripAdvisor hotels URL
        hotels_url = f"{self.BASE_URL}/Hotels-g{location.replace(' ', '_')}"
        response = await self._make_request(hotels_url)
        
        if response:
            # Parse HTML using BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract hotel data from HTML
            hotel_elements = soup.find_all(['div', 'article'], class_=lambda x: bool(x and ('hotel' in x.lower() or 'property' in x.lower() or 'listing' in x.lower())))
            
            for element in hotel_elements[:limit]:
                name_elem = element.find(['h2', 'h3', 'a'], class_=lambda x: bool(x and 'name' in x.lower()))
                name = name_elem.get_text(strip=True) if name_elem else f"Hotel in {location}"
                
                rating_elem = element.find(class_=lambda x: bool(x and 'rating' in x.lower()))
                rating = None
                if rating_elem:
                    rating_text = rating_elem.get_text(strip=True)
                    try:
                        rating = float(rating_text.split()[0])
                    except (ValueError, IndexError):
                        pass
                
                price_elem = element.find(class_=lambda x: bool(x and ('price' in x.lower() or 'rate' in x.lower())))
                price_range = price_elem.get_text(strip=True) if price_elem else None
                
                description_elem = element.find(['p', 'div'], class_=lambda x: bool(x and ('description' in x.lower() or 'text' in x.lower())))
                description = description_elem.get_text(strip=True) if description_elem else ""
                
                hotel_data = {
                    "name": name,
                    "location": location,
                    "description": description or "Data from TripAdvisor",
                    "rating": rating,
                    "price_range": price_range,
                    "source_url": hotels_url,
                }
                results.append(self._add_source_metadata(hotel_data))
            
            # If no structured data found, return basic info
            if not results:
                hotel_data = {
                    "name": f"Hotel in {location}",
                    "location": location,
                    "description": "Data from TripAdvisor (may require JavaScript rendering)",
                    "source_url": hotels_url,
                }
                results.append(self._add_source_metadata(hotel_data))
        
        return results
    
    async def fetch_restaurants(self, location: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch restaurants from TripAdvisor"""
        results = []
        
        # TripAdvisor restaurants URL
        restaurants_url = f"{self.BASE_URL}/Restaurants-g{location.replace(' ', '_')}"
        response = await self._make_request(restaurants_url)
        
        if response:
            # Parse HTML using BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract restaurant data from HTML
            restaurant_elements = soup.find_all(['div', 'article'], class_=lambda x: bool(x and ('restaurant' in x.lower() or 'dining' in x.lower() or 'listing' in x.lower())))
            
            for element in restaurant_elements[:limit]:
                name_elem = element.find(['h2', 'h3', 'a'], class_=lambda x: bool(x and 'name' in x.lower()))
                name = name_elem.get_text(strip=True) if name_elem else f"Restaurant in {location}"
                
                rating_elem = element.find(class_=lambda x: bool(x and 'rating' in x.lower()))
                rating = None
                if rating_elem:
                    rating_text = rating_elem.get_text(strip=True)
                    try:
                        rating = float(rating_text.split()[0])
                    except (ValueError, IndexError):
                        pass
                
                cuisine_elem = element.find(class_=lambda x: bool(x and ('cuisine' in x.lower() or 'type' in x.lower())))
                cuisine_type = cuisine_elem.get_text(strip=True) if cuisine_elem else None
                
                price_elem = element.find(class_=lambda x: bool(x and ('price' in x.lower() or 'cost' in x.lower())))
                price_range = price_elem.get_text(strip=True) if price_elem else None
                
                description_elem = element.find(['p', 'div'], class_=lambda x: bool(x and ('description' in x.lower() or 'text' in x.lower())))
                description = description_elem.get_text(strip=True) if description_elem else ""
                
                restaurant_data = {
                    "name": name,
                    "location": location,
                    "description": description or "Data from TripAdvisor",
                    "rating": rating,
                    "cuisine_type": cuisine_type,
                    "price_range": price_range,
                    "source_url": restaurants_url,
                }
                results.append(self._add_source_metadata(restaurant_data))
            
            # If no structured data found, return basic info
            if not results:
                restaurant_data = {
                    "name": f"Restaurant in {location}",
                    "location": location,
                    "description": "Data from TripAdvisor (may require JavaScript rendering)",
                    "source_url": restaurants_url,
                }
                results.append(self._add_source_metadata(restaurant_data))
        
        return results

