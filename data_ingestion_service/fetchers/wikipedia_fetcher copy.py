"""
Wikipedia fetcher using MediaWiki API
"""
from typing import Any, Dict, List

import httpx
from bs4 import BeautifulSoup

from .base_fetcher import BaseFetcher

try:
    import html2text
    HTML2TEXT_AVAILABLE = True
except ImportError:
    HTML2TEXT_AVAILABLE = False


class WikipediaFetcher(BaseFetcher):
    """Fetcher for Wikipedia data using MediaWiki API"""
    
    BASE_URL = "https://en.wikipedia.org/api/rest_v1"
    
    @property
    def source_name(self) -> str:
        return "wikipedia"
    
    async def fetch_country_info(self, country_name: str) -> List[Dict[str, Any]]:
        """
        Fetch country information from Wikipedia - returns Markdown content
        
        Args:
            country_name: Query to search on Wikipedia (e.g., "Poland", "Warsaw")
        
        Returns:
            List with single dict containing Markdown content from Wikipedia page
        """
        results = []
        
        # Get full page HTML content
        content_url = f"{self.BASE_URL}/page/html/{country_name}"
        response = await self._make_request(content_url)
        
        if response:
            # Save original HTML if output_dir is set
            if self.output_dir:
                from ..utils import save_html_file
                save_html_file(
                    self.output_dir,
                    self.source_name,
                    country_name,
                    response.text
                )
            
            # Parse HTML content using BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Convert HTML to Markdown
            markdown_content = self._convert_html_to_markdown(soup)
            
            # Get page URL for source_url
            source_url = f"https://en.wikipedia.org/wiki/{country_name.replace(' ', '_')}"
            
            # Return markdown content as description
            result = {
                "name": country_name,
                "description": markdown_content,  # Main field with markdown content
                "source_url": source_url,
            }
            results.append(self._add_source_metadata(result))
        
        return results
    
    async def fetch_attractions(self, location: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch attractions from Wikipedia"""
        results = []
        
        # Search for pages related to attractions in location
        search_url = f"{self.BASE_URL}/page/summary/{location}_attractions"
        response = await self._make_request(search_url)
        
        if response:
            data = response.json()
            attraction_data = {
                "name": data.get("title", f"{location} Attractions"),
                "location": location,
                "description": data.get("extract", ""),
                "source_url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            }
            results.append(self._add_source_metadata(attraction_data))
        
        return results
    
    def _convert_html_to_markdown(self, soup: BeautifulSoup) -> str:
        """
        Convert HTML content to Markdown format
        
        Args:
            soup: BeautifulSoup object of the HTML page
        
        Returns:
            Markdown content (preserves tables, links, formatting)
        """
        # Remove script, style, and other non-content elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
            element.decompose()
        
        # Find main content area (mw-parser-output is Wikipedia's main content div)
        main_content = soup.find("div", class_="mw-parser-output")
        if not main_content:
            # Fallback: try to find body or main content
            main_content = soup.find("body") or soup.find("main") or soup
        
        if HTML2TEXT_AVAILABLE:
            # Use html2text for proper Markdown conversion (preserves tables, links, etc.)
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = False
            h.body_width = 0  # Don't wrap lines
            h.unicode_snob = True  # Use unicode characters
            markdown_content = h.handle(str(main_content))
        else:
            # Fallback: basic text extraction if html2text not available
            text = main_content.get_text(separator="\n", strip=True)
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            markdown_content = '\n'.join(chunk for chunk in chunks if chunk)
        
        return markdown_content

