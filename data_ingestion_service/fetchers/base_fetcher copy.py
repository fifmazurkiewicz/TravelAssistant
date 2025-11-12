"""
Base fetcher class for all data sources
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class BaseFetcher(ABC):
    """Base class for all data fetchers"""
    
    def __init__(self, rate_limit_delay: float = 1.0, timeout: int = 30, output_dir: Optional[Path] = None):
        """
        Initialize base fetcher
        
        Args:
            rate_limit_delay: Delay between requests in seconds
            timeout: Request timeout in seconds
            output_dir: Optional output directory for saving HTML files
        """
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout
        self.output_dir = output_dir
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        # Wikipedia and other APIs require User-Agent header
        headers = {
            "User-Agent": "TravelAssistant/1.0 (https://github.com/yourusername/travelassistant; contact@example.com)"
        }
        self.client = httpx.AsyncClient(timeout=self.timeout, headers=headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Name of the data source"""
        pass
    
    @abstractmethod
    async def fetch_country_info(self, country_name: str) -> List[Dict[str, Any]]:
        """
        Fetch country information
        
        Args:
            country_name: Name of the country to fetch
            
        Returns:
            List of dictionaries with country information
        """
        pass
    
    @abstractmethod
    async def fetch_attractions(self, location: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch attractions for a location
        
        Args:
            location: Location name (city or country)
            limit: Maximum number of results
            
        Returns:
            List of dictionaries with attraction information
        """
        pass
    
    async def fetch_hotels(self, location: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch hotels for a location (optional, not all sources have hotels)
        
        Args:
            location: Location name
            limit: Maximum number of results
            
        Returns:
            List of dictionaries with hotel information
        """
        return []
    
    async def fetch_restaurants(self, location: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch restaurants for a location (optional, not all sources have restaurants)
        
        Args:
            location: Location name
            limit: Maximum number of results
            
        Returns:
            List of dictionaries with restaurant information
        """
        return []
    
    async def _make_request(self, url: str, **kwargs) -> Optional[httpx.Response]:
        """
        Make HTTP request with rate limiting
        
        Args:
            url: URL to request
            **kwargs: Additional arguments for httpx
            
        Returns:
            Response object or None if error
        """
        if not self.client:
            raise RuntimeError("Fetcher must be used as async context manager")
        
        try:
            await asyncio.sleep(self.rate_limit_delay)
            response = await self.client.get(url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPError as e:
            logger.warning(f"Error fetching {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}", exc_info=True)
            return None
    
    def _add_source_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add source metadata to data"""
        data["source"] = self.source_name
        data["fetched_at"] = datetime.utcnow().isoformat()
        return data

