"""
Lonely Planet fetcher using web scraping
"""
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from .base_fetcher import BaseFetcher


class LonelyPlanetFetcher(BaseFetcher):
    """Fetcher for Lonely Planet data using web scraping"""
    
    BASE_URL = "https://www.lonelyplanet.com"
    
    @property
    def source_name(self) -> str:
        return "lonely_planet"
    
    async def fetch_country_info(self, country_name: str) -> List[Dict[str, Any]]:
        """Fetch country information from Lonely Planet"""
        results = []
        
        # Lonely Planet country guide URL
        country_url = f"{self.BASE_URL}/{country_name.lower().replace(' ', '-')}"
        response = await self._make_request(country_url)
        
        if response:
            # Save original HTML if output_dir is set
            if self.output_dir:
                from utils.file_manager import save_html_file
                save_html_file(
                    self.output_dir,
                    self.source_name,
                    country_name,  # query = country_name
                    response.text
                )
            
            # Parse HTML using BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract country information
            # Try to find main content
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=lambda x: bool(x and 'content' in x.lower()))
            
            description = ""
            if main_content:
                # Extract text from main content
                paragraphs = main_content.find_all('p')
                description = ' '.join([p.get_text(strip=True) for p in paragraphs[:5]])  # First 5 paragraphs
            
            # Try to find specific sections
            intro = soup.find(['div', 'section'], class_=lambda x: bool(x and ('intro' in x.lower() or 'overview' in x.lower())))
            if intro:
                description = intro.get_text(strip=True)
            
            country_data = {
                "name": country_name,
                "description": description or "Data from Lonely Planet guide",
                "source_url": country_url,
            }
            results.append(self._add_source_metadata(country_data))
        
        return results
    
    async def fetch_attractions(self, location: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch attractions from Lonely Planet"""
        results = []
        
        # Lonely Planet attractions URL
        attractions_url = f"{self.BASE_URL}/{location.lower().replace(' ', '-')}/attractions"
        response = await self._make_request(attractions_url)
        
        if response:
            # Parse HTML using BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract attractions
            attraction_elements = soup.find_all(['article', 'div'], class_=lambda x: bool(x and ('attraction' in x.lower() or 'place' in x.lower() or 'poi' in x.lower())))
            
            for element in attraction_elements[:limit]:
                name_elem = element.find(['h2', 'h3', 'h4', 'a'])
                name = name_elem.get_text(strip=True) if name_elem else f"Attraction in {location}"
                
                description_elem = element.find(['p', 'div'], class_=lambda x: bool(x and ('description' in x.lower() or 'text' in x.lower() or 'summary' in x.lower())))
                description = description_elem.get_text(strip=True) if description_elem else ""
                
                attraction_data = {
                    "name": name,
                    "location": location,
                    "description": description or "Data from Lonely Planet",
                    "source_url": attractions_url,
                }
                results.append(self._add_source_metadata(attraction_data))
            
            # If no structured data found, return basic info
            if not results:
                attraction_data = {
                    "name": f"Attraction in {location}",
                    "location": location,
                    "description": "Data from Lonely Planet",
                    "source_url": attractions_url,
                }
                results.append(self._add_source_metadata(attraction_data))
        
        return results

