"""
World Travel Guide fetcher using web scraping
"""
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from .base_fetcher import BaseFetcher


class WorldTravelGuideFetcher(BaseFetcher):
    """Fetcher for World Travel Guide data using web scraping"""
    
    BASE_URL = "https://www.worldtravelguide.net"
    
    @property
    def source_name(self) -> str:
        return "world_travel_guide"
    
    async def fetch_country_info(self, country_name: str) -> List[Dict[str, Any]]:
        """Fetch country information from World Travel Guide"""
        results = []
        
        # World Travel Guide country URL
        country_url = f"{self.BASE_URL}/guides/{country_name.lower().replace(' ', '-')}"
        response = await self._make_request(country_url)
        
        if response:
            # Parse HTML using BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract country information
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=lambda x: bool(x and 'content' in x.lower()))
            
            description = ""
            if main_content:
                # Extract text from main content
                paragraphs = main_content.find_all('p')
                description = ' '.join([p.get_text(strip=True) for p in paragraphs[:5]])
            
            # Try to find intro or overview section
            intro = soup.find(['div', 'section'], class_=lambda x: bool(x and ('intro' in x.lower() or 'overview' in x.lower() or 'summary' in x.lower())))
            if intro:
                description = intro.get_text(strip=True)
            
            country_data = {
                "name": country_name,
                "description": description or "Data from World Travel Guide",
                "source_url": country_url,
            }
            results.append(self._add_source_metadata(country_data))
        
        return results
    
    async def fetch_attractions(self, location: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch attractions from World Travel Guide"""
        results = []
        
        # World Travel Guide attractions URL
        attractions_url = f"{self.BASE_URL}/guides/{location.lower().replace(' ', '-')}/attractions"
        response = await self._make_request(attractions_url)
        
        if response:
            # Parse HTML using BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract attractions
            attraction_elements = soup.find_all(['article', 'div', 'li'], class_=lambda x: bool(x and ('attraction' in x.lower() or 'place' in x.lower() or 'sight' in x.lower() or 'poi' in x.lower())))
            
            for element in attraction_elements[:limit]:
                name_elem = element.find(['h2', 'h3', 'h4', 'a', 'strong'])
                name = name_elem.get_text(strip=True) if name_elem else f"Attraction in {location}"
                
                description_elem = element.find(['p', 'div', 'span'], class_=lambda x: bool(x and ('description' in x.lower() or 'text' in x.lower() or 'summary' in x.lower())))
                description = description_elem.get_text(strip=True) if description_elem else ""
                
                # If no description found, use all text from element
                if not description:
                    description = element.get_text(strip=True)[:500]  # Limit to 500 chars
                
                attraction_data = {
                    "name": name,
                    "location": location,
                    "description": description or "Data from World Travel Guide",
                    "source_url": attractions_url,
                }
                results.append(self._add_source_metadata(attraction_data))
            
            # If no structured data found, return basic info
            if not results:
                attraction_data = {
                    "name": f"Attraction in {location}",
                    "location": location,
                    "description": "Data from World Travel Guide",
                    "source_url": attractions_url,
                }
                results.append(self._add_source_metadata(attraction_data))
        
        return results

