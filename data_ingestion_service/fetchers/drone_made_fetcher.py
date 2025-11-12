"""
Drone Made fetcher - scrapes drone-made.com, saves HTML and parses to text
"""
from typing import Any, Dict, List
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from .base_fetcher import BaseFetcher


class DroneMadeFetcher(BaseFetcher):
    """Fetcher for drone-made.com - saves HTML and parses to text"""
    
    BASE_URL = "https://www.drone-made.com"
    
    @property
    def source_name(self) -> str:
        return "drone_made"
    
    def _normalize_country_name(self, country_name: str) -> str:
        """
        Normalize country name for URL
        
        Examples:
            "Poland" -> "poland-drone-laws"
            "United States" -> "united-states-drone-laws"
        """
        country_lower = country_name.lower().strip()
        return f"{country_lower.replace(' ', '-')}-drone-laws"
    
    async def fetch_country_info(self, country_name: str) -> List[Dict[str, Any]]:
        """
        Fetch drone laws information from drone-made.com
        
        Args:
            country_name: Name of the country (e.g., "Poland")
        
        Returns:
            List with single dict containing parsed text
        """
        results = []
        
        # Normalize country name for URL
        country_normalized = self._normalize_country_name(country_name)
        url = f"{self.BASE_URL}/post/{country_normalized}"
        
        # Fetch HTML
        response = await self._make_request(url)
        
        if not response:
            return results
        
        # Parse HTML to text
        soup = BeautifulSoup(response.text, 'html.parser')
        text_content = self._extract_text_from_html(soup)
        
        # Don't save here - will be saved via save_html_and_text_to_country_folder from WikivoyageFetcher
        # This prevents duplicate files in old folder structure
        
        result = {
            "name": country_name,
            "description": text_content,
            "source_url": url,
        }
        results.append(self._add_source_metadata(result))
        
        return results
    
    def _extract_text_from_html(self, soup: BeautifulSoup) -> str:
        """
        Extract text content from HTML (no HTML tags)
        
        Args:
            soup: BeautifulSoup object of the HTML page
        
        Returns:
            Clean text content without HTML tags
        """
        # Remove script, style, and other non-content elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
            element.decompose()
        
        # Find main content area
        main_content = soup.find("main") or soup.find("article") or soup.find("body")
        if not main_content:
            main_content = soup
        
        # Extract text from main content
        text = main_content.get_text(separator=" ", strip=True)
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def _save_html(self, country_name: str, html_content: str) -> Path:
        """
        Save HTML content to file
        
        Args:
            country_name: Name of the country
            html_content: HTML content to save
        
        Returns:
            Path to saved HTML file
        """
        country_safe = country_name.lower().replace(" ", "_")
        drone_made_folder = self.output_dir / "drone_made" / country_safe
        drone_made_folder.mkdir(parents=True, exist_ok=True)
        
        html_file = drone_made_folder / "drone_made_com.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return html_file
    
    def _save_text(self, country_name: str, text_content: str) -> Path:
        """
        Save text content to file
        
        Args:
            country_name: Name of the country
            text_content: Text content to save
        
        Returns:
            Path to saved text file
        """
        country_safe = country_name.lower().replace(" ", "_")
        drone_made_folder = self.output_dir / "drone_made" / country_safe
        drone_made_folder.mkdir(parents=True, exist_ok=True)
        
        text_file = drone_made_folder / "drone_made_com.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        return text_file
    
    async def fetch_attractions(self, location: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Not applicable for drone made"""
        return []
    
    def save_html_and_text_to_source(self, country_name: str, html_content: str) -> tuple:
        """
        Save HTML and parsed text to drone_laws source folder
        
        Args:
            country_name: Name of the country (e.g., "Poland")
            html_content: HTML content to save
        
        Returns:
            Tuple of (html_path, text_path)
        """
        if not self.output_dir:
            raise ValueError("output_dir must be set")
        
        country_safe = country_name.lower().replace(" ", "_")
        drone_laws_folder = self.output_dir / "drone_laws" / country_safe
        drone_laws_folder.mkdir(parents=True, exist_ok=True)
        
        # Save HTML
        html_file = drone_laws_folder / "drone_made_com.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Parse HTML to text
        soup = BeautifulSoup(html_content, 'html.parser')
        text_content = self._extract_text_from_html(soup)
        
        # Save text
        text_file = drone_laws_folder / "drone_made_com.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        return html_file, text_file
    
    def save_html_and_text_to_country_folder(self, country_folder: Path, html_content: str) -> tuple:
        """
        DEPRECATED: Use save_html_and_text_to_source instead
        Save HTML and parsed text to country folder (kept for backward compatibility)
        """
        # Extract country name from folder path for backward compatibility
        country_name = country_folder.name
        return self.save_html_and_text_to_source(country_name, html_content)

