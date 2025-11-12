"""
Data fetchers for external sources

Metody pobierania danych:
- WikipediaFetcher: MediaWiki REST API
- WikidataFetcher: SPARQL queries
- Pozostałe fetchery: Web scraping z BeautifulSoup
"""
from .base_fetcher import BaseFetcher
from .lonely_planet_fetcher import LonelyPlanetFetcher
from .travel_independent_fetcher import TravelIndependentFetcher
from .tripadvisor_fetcher import TripAdvisorFetcher
from .wikidata_fetcher import WikidataFetcher
from .wikipedia_fetcher import WikipediaFetcher
from .wikivoyage_fetcher import WikivoyageFetcher
from .world_travel_guide_fetcher import WorldTravelGuideFetcher
from .drone_laws_fetcher import DroneLawsFetcher
from .drone_made_fetcher import DroneMadeFetcher

__all__ = [
    "BaseFetcher",
    "WikipediaFetcher",
    "WikidataFetcher",
    "WikivoyageFetcher",
    "TripAdvisorFetcher",
    "LonelyPlanetFetcher",
    "WorldTravelGuideFetcher",
    "TravelIndependentFetcher",
    "DroneLawsFetcher",
    "DroneMadeFetcher",
]

