"""
Drone Laws fetcher - scrapes drone-laws.com and converts to Markdown
"""
from typing import Any, Dict, List
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from .base_fetcher import BaseFetcher

try:
    import html2text
    HTML2TEXT_AVAILABLE = True
except ImportError:
    HTML2TEXT_AVAILABLE = False


class DroneLawsFetcher(BaseFetcher):
    """Fetcher for drone-laws.com - converts HTML to Markdown"""
    
    BASE_URL = "https://drone-laws.com"
    
    @property
    def source_name(self) -> str:
        return "drone_laws"
    
    def _normalize_country_name(self, country_name: str) -> str:
        """
        Normalize country name for URL
        
        Examples:
            "Poland" -> "poland"
            "United States" -> "united-states"
            "United Kingdom" -> "uk"
        """
        # Known mappings
        country_mappings = {
            "united states": "united-states",
            "united kingdom": "uk",
            "czech republic": "czech-republic",
            "south korea": "south-korea",
            "north korea": "north-korea",
        }
        
        country_lower = country_name.lower().strip()
        if country_lower in country_mappings:
            return country_mappings[country_lower]
        
        # Default: lowercase and replace spaces with hyphens
        return country_lower.replace(" ", "-")
    
    async def fetch_country_info(self, country_name: str) -> List[Dict[str, Any]]:
        """
        Fetch drone laws information from drone-laws.com
        
        Args:
            country_name: Name of the country (e.g., "Poland")
        
        Returns:
            List with single dict containing markdown content
        """
        results = []
        
        # Normalize country name for URL
        country_normalized = self._normalize_country_name(country_name)
        url = f"{self.BASE_URL}/drone-laws-in-{country_normalized}/"
        
        # Fetch HTML
        response = await self._make_request(url)
        
        if not response:
            return results
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Convert HTML to Markdown
        if HTML2TEXT_AVAILABLE:
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = False
            h.body_width = 0  # Don't wrap lines
            markdown_content = h.handle(str(soup))
        else:
            # Fallback: basic text extraction if html2text not available
            # Remove script and style elements
            for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
                element.decompose()
            
            # Get main content
            main_content = soup.find("main") or soup.find("article") or soup.find("body")
            if main_content:
                markdown_content = main_content.get_text(separator="\n", strip=True)
            else:
                markdown_content = soup.get_text(separator="\n", strip=True)
        
        # Don't save here - will be saved via save_markdown_to_country_folder from WikivoyageFetcher
        # This prevents duplicate files in old folder structure
        
        result = {
            "name": country_name,
            "description": markdown_content,
            "source_url": url,
        }
        results.append(self._add_source_metadata(result))
        
        return results
    
    def _save_markdown(self, country_name: str, markdown_content: str) -> Path:
        """
        Save markdown content to file
        
        Args:
            country_name: Name of the country
            markdown_content: Markdown content to save
        
        Returns:
            Path to saved markdown file
        """
        # This will be called from WikivoyageFetcher with country folder path
        # For now, save to output_dir/drone_laws/{country}/drone_laws_com.md
        country_safe = country_name.lower().replace(" ", "_")
        drone_laws_folder = self.output_dir / "drone_laws" / country_safe
        drone_laws_folder.mkdir(parents=True, exist_ok=True)
        
        markdown_file = drone_laws_folder / "drone_laws_com.md"
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return markdown_file
    
    async def fetch_attractions(self, location: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Not applicable for drone laws"""
        return []
    
    def save_markdown_to_source(self, country_name: str, markdown_content: str) -> Path:
        """
        Save markdown content to drone_laws source folder
        
        Args:
            country_name: Name of the country (e.g., "Poland")
            markdown_content: Markdown content to save
        
        Returns:
            Path to saved markdown file
        """
        if not self.output_dir:
            raise ValueError("output_dir must be set")
        
        country_safe = country_name.lower().replace(" ", "_")
        drone_laws_folder = self.output_dir / "drone_laws" / country_safe
        drone_laws_folder.mkdir(parents=True, exist_ok=True)
        
        markdown_file = drone_laws_folder / "drone_laws_com.md"
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return markdown_file
    
    def save_markdown_to_country_folder(self, country_folder: Path, markdown_content: str) -> Path:
        """
        DEPRECATED: Use save_markdown_to_source instead
        Save markdown content to country folder (kept for backward compatibility)
        """
        # Extract country name from folder path for backward compatibility
        country_name = country_folder.name
        return self.save_markdown_to_source(country_name, markdown_content)

