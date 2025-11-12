"""
Travel Independent fetcher using web scraping
"""
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from .base_fetcher import BaseFetcher


class TravelIndependentFetcher(BaseFetcher):
    """Fetcher for Travel Independent data using web scraping"""
    
    BASE_URL = "https://www.travelindependent.info"
    
    @property
    def source_name(self) -> str:
        return "travel_independent"
    
    async def fetch_country_info(self, country_name: str) -> List[Dict[str, Any]]:
        """Fetch country information from Travel Independent"""
        results = []
        
        # Travel Independent country URL
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
            main_content = soup.find('main') or soup.find('article') or soup.find('div', id='content') or soup.find('div', class_=lambda x: bool(x and 'content' in x.lower()))
            
            description = ""
            if main_content:
                # Extract text from main content
                paragraphs = main_content.find_all('p')
                description = ' '.join([p.get_text(strip=True) for p in paragraphs[:5]])
            
            # Try to find intro section
            intro = soup.find(['div', 'section'], class_=lambda x: bool(x and ('intro' in x.lower() or 'overview' in x.lower())))
            if intro:
                description = intro.get_text(strip=True)
            
            country_data = {
                "name": country_name,
                "description": description or "Data from Travel Independent",
                "source_url": country_url,
            }
            results.append(self._add_source_metadata(country_data))
        
        return results
    
    async def fetch_attractions(self, location: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch attractions from Travel Independent"""
        results = []
        
        # Travel Independent location URL
        location_url = f"{self.BASE_URL}/{location.lower().replace(' ', '-')}"
        response = await self._make_request(location_url)
        
        if response:
            # Parse HTML using BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract location information
            main_content = soup.find('main') or soup.find('article') or soup.find('div', id='content')
            
            description = ""
            if main_content:
                paragraphs = main_content.find_all('p')
                description = ' '.join([p.get_text(strip=True) for p in paragraphs[:5]])
            
            # Try to find sections about places to visit or attractions
            attractions_section = soup.find(['div', 'section'], class_=lambda x: bool(x and ('attraction' in x.lower() or 'place' in x.lower() or 'visit' in x.lower() or 'see' in x.lower())))
            if attractions_section:
                description = attractions_section.get_text(strip=True)
            
            location_data = {
                "name": f"Travel info for {location}",
                "location": location,
                "description": description or "Data from Travel Independent",
                "source_url": location_url,
            }
            results.append(self._add_source_metadata(location_data))
        else:
            # Fallback if request fails
            location_data = {
                "name": f"Travel info for {location}",
                "location": location,
                "description": "Data from Travel Independent",
                "source_url": f"{self.BASE_URL}/{location.lower().replace(' ', '-')}",
            }
            results.append(self._add_source_metadata(location_data))
        
        return results

