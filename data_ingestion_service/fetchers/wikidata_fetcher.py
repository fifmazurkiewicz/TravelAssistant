"""
Wikidata fetcher using SPARQL queries
"""
from typing import Any, Dict, List

from .base_fetcher import BaseFetcher


class WikidataFetcher(BaseFetcher):
    """Fetcher for Wikidata using SPARQL queries"""
    
    SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
    
    @property
    def source_name(self) -> str:
        return "wikidata"
    
    async def fetch_country_info(self, country_name: str) -> List[Dict[str, Any]]:
        """Fetch country information from Wikidata using SPARQL"""
        results = []
        
        # SPARQL query to get country information
        query = f"""
        SELECT ?country ?countryLabel ?capital ?capitalLabel ?population ?area ?currency ?currencyLabel
        WHERE {{
            ?country wdt:P31 wd:Q6256 .  # instance of country
            ?country rdfs:label ?countryLabel .
            FILTER(LANG(?countryLabel) = "en") .
            FILTER(CONTAINS(LCASE(?countryLabel), "{country_name.lower()}")) .
            OPTIONAL {{ ?country wdt:P36 ?capital . }}
            OPTIONAL {{ ?capital rdfs:label ?capitalLabel . FILTER(LANG(?capitalLabel) = "en") . }}
            OPTIONAL {{ ?country wdt:P1082 ?population . }}
            OPTIONAL {{ ?country wdt:P2046 ?area . }}
            OPTIONAL {{ ?country wdt:P38 ?currency . }}
            OPTIONAL {{ ?currency rdfs:label ?currencyLabel . FILTER(LANG(?currencyLabel) = "en") . }}
        }}
        LIMIT 1
        """
        
        response = await self._make_request(
            self.SPARQL_ENDPOINT,
            params={"query": query, "format": "json"}
        )
        
        if response:
            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])
            
            for binding in bindings:
                country_data = {
                    "name": binding.get("countryLabel", {}).get("value", country_name),
                    "capital": binding.get("capitalLabel", {}).get("value"),
                    "population": int(binding.get("population", {}).get("value", 0)) if binding.get("population") else None,
                    "area_km2": float(binding.get("area", {}).get("value", 0)) if binding.get("area") else None,
                    "currency": binding.get("currencyLabel", {}).get("value"),
                    "source_url": binding.get("country", {}).get("value", ""),
                }
                results.append(self._add_source_metadata(country_data))
        
        return results
    
    async def fetch_attractions(self, location: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch attractions from Wikidata"""
        results = []
        
        # SPARQL query for tourist attractions
        query = f"""
        SELECT ?attraction ?attractionLabel ?location ?locationLabel ?coordinates
        WHERE {{
            ?attraction wdt:P31/wdt:P279* wd:Q570116 .  # tourist attraction
            ?attraction wdt:P131 ?location .  # located in
            ?location rdfs:label ?locationLabel .
            FILTER(LANG(?locationLabel) = "en") .
            FILTER(CONTAINS(LCASE(?locationLabel), "{location.lower()}")) .
            ?attraction rdfs:label ?attractionLabel .
            FILTER(LANG(?attractionLabel) = "en") .
            OPTIONAL {{ ?attraction wdt:P625 ?coordinates . }}
        }}
        LIMIT {limit}
        """
        
        response = await self._make_request(
            self.SPARQL_ENDPOINT,
            params={"query": query, "format": "json"}
        )
        
        if response:
            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])
            
            for binding in bindings:
                attraction_data = {
                    "name": binding.get("attractionLabel", {}).get("value", ""),
                    "location": binding.get("locationLabel", {}).get("value", location),
                    "source_url": binding.get("attraction", {}).get("value", ""),
                }
                
                # Parse coordinates if available
                coords = binding.get("coordinates", {}).get("value")
                if coords:
                    # Wikidata coordinates format: "Point(lon lat)"
                    attraction_data["coordinates"] = self._parse_wikidata_coordinates(coords)
                
                results.append(self._add_source_metadata(attraction_data))
        
        return results
    
    def _parse_wikidata_coordinates(self, coords_str: str) -> Dict[str, float]:
        """Parse Wikidata coordinate string to lat/lon dict"""
        try:
            # Format: "Point(lon lat)"
            coords_str = coords_str.replace("Point(", "").replace(")", "")
            parts = coords_str.split()
            if len(parts) >= 2:
                return {
                    "lon": float(parts[0]),
                    "lat": float(parts[1])
                }
        except (ValueError, IndexError):
            pass
        return {}

