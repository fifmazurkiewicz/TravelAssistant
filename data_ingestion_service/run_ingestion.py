"""
Main orchestration script for data ingestion
"""
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import fetchers, models, processors using absolute imports
# Since run_ingestion.py is in the root of data_ingestion_service,
# we can import directly from submodules
from fetchers import (
    WikidataFetcher,
    WikipediaFetcher,
    WikivoyageFetcher,
)
from models import Attraction, CountryInfo, HotelOffer, RestaurantInfo
from processors import DataStandardizer
from utils.file_manager import get_output_file_path, group_by_source

# Import LLM processor conditionally
try:
    from processors.llm_processor import LLMProcessor
except ImportError:
    LLMProcessor = None


class DataIngestionOrchestrator:
    """Orchestrates data ingestion from multiple sources"""
    
    def __init__(
        self,
        enabled_sources: Optional[List[str]] = None,
        output_dir: str = "./data_ingestion_output",
        wikivoyage_language: str = "en",
        wikivoyage_max_depth: int = 1,
        wikivoyage_level_1_sections: Optional[List[str]] = None,
        wikivoyage_level_2_sections: Optional[List[str]] = None,
        use_llm: bool = False,
        llm_api_key: Optional[str] = None,
        llm_base_url: str = "https://openrouter.ai/api/v1",
        llm_model: str = "openrouter/anthropic/claude-3-haiku"
    ):
        """
        Initialize orchestrator
        
        Args:
            enabled_sources: List of source names to enable (None = all)
            output_dir: Directory to save output files
            wikivoyage_language: Language code for Wikivoyage (en, pl, de, etc.). Default: en
            wikivoyage_max_depth: How many levels deep to fetch (1 = country -> cities, 2 = country -> cities -> attractions). Default: 1
            wikivoyage_level_1_sections: List of section names for level 1 (e.g., ["Cities", "Cities and towns"]). Default: ["Cities", "Cities and towns"]
            wikivoyage_level_2_sections: List of section names for level 2 (e.g., ["See", "Do"]). Default: ["See", "Do"]
            use_llm: Whether to use LLM for data analysis and structuring
            llm_api_key: OpenRouter API key for LLM processing
            llm_base_url: OpenRouter base URL
            llm_model: LLM model to use
        """
        self.enabled_sources = enabled_sources or [
            "wikipedia",
            "wikidata",
            "wikivoyage"
        ]
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.wikivoyage_language = wikivoyage_language
        self.wikivoyage_max_depth = wikivoyage_max_depth
        self.wikivoyage_level_1_sections = wikivoyage_level_1_sections
        self.wikivoyage_level_2_sections = wikivoyage_level_2_sections
        self.use_llm = use_llm
        
        self.standardizer = DataStandardizer()
        self.fetchers = self._initialize_fetchers()
        
        # Initialize LLM processor if enabled
        self.llm_processor = None
        if use_llm and llm_api_key:
            if LLMProcessor is None:
                print("Warning: LLMProcessor not available. Install openai package: pip install openai")
                self.use_llm = False
            else:
                try:
                    self.llm_processor = LLMProcessor(
                        api_key=llm_api_key,
                        base_url=llm_base_url,
                        model=llm_model
                    )
                except Exception as e:
                    print(f"Warning: Could not initialize LLM processor: {e}")
                    self.use_llm = False
    
    def _initialize_fetchers(self) -> Dict[str, Any]:
        """Initialize fetchers based on enabled sources"""
        fetcher_classes = {
            "wikipedia": WikipediaFetcher,
            "wikidata": WikidataFetcher,
            "wikivoyage": WikivoyageFetcher,
        }
        
        fetchers = {}
        for source in self.enabled_sources:
            if source in fetcher_classes:
                # Special handling for Wikivoyage to support language, max_depth, and sections parameters
                if source == "wikivoyage":
                    fetchers[source] = fetcher_classes[source](
                        language=self.wikivoyage_language,
                        output_dir=self.output_dir,
                        max_depth=self.wikivoyage_max_depth,
                        level_1_sections=self.wikivoyage_level_1_sections,
                        level_2_sections=self.wikivoyage_level_2_sections
                    )
                else:
                    fetchers[source] = fetcher_classes[source](output_dir=self.output_dir)
        
        return fetchers
    
    async def fetch_country_data(self, country_name: str) -> Dict[str, List[Any]]:
        """Fetch country data from all enabled sources"""
        results = {
            "countries": [],
            "attractions": [],
            "hotels": [],
            "restaurants": []
        }
        
        # Process each fetcher separately to keep context manager alive
        for source_name, fetcher in self.fetchers.items():
            async with fetcher:
                # Create all tasks for this fetcher
                tasks = []
                
                # Fetch country info
                task = fetcher.fetch_country_info(country_name)
                tasks.append(("country", source_name, task))
                
                # Fetch attractions
                task = fetcher.fetch_attractions(country_name, limit=10)
                tasks.append(("attractions", source_name, task))
                
                # Fetch hotels (if supported)
                task = fetcher.fetch_hotels(country_name, limit=10)
                tasks.append(("hotels", source_name, task))
                
                # Fetch restaurants (if supported)
                task = fetcher.fetch_restaurants(country_name, limit=10)
                tasks.append(("restaurants", source_name, task))
                
                # Execute all tasks for this fetcher BEFORE exiting context manager
                for data_type, source_name, task in tasks:
                    try:
                        raw_data = await task
                        if raw_data:
                            # Apply LLM analysis for Wikivoyage data
                            if self.use_llm and self.llm_processor and source_name.startswith("wikivoyage"):
                                if data_type == "country":
                                    # Analyze country info with LLM
                                    for item in raw_data:
                                        if "full_content" in item or "sections" in item:
                                            analyzed = await self.llm_processor.analyze_wikivoyage_content(
                                                country_name=country_name,
                                                raw_content=item.get("full_content", ""),
                                                sections=item.get("sections", {})
                                            )
                                            # Merge analyzed data with original
                                            item.update(analyzed)
                                
                                elif data_type == "attractions":
                                    # Enhance attractions with LLM
                                    raw_data = await self.llm_processor.enhance_attractions(raw_data)
                            
                            # Standardize data
                            if data_type == "country":
                                standardized = self.standardizer.standardize_country_info(raw_data)
                                results["countries"].extend(standardized)
                            elif data_type == "attractions":
                                standardized = self.standardizer.standardize_attractions(raw_data)
                                results["attractions"].extend(standardized)
                            elif data_type == "hotels":
                                standardized = self.standardizer.standardize_hotels(raw_data)
                                results["hotels"].extend(standardized)
                            elif data_type == "restaurants":
                                standardized = self.standardizer.standardize_restaurants(raw_data)
                                results["restaurants"].extend(standardized)
                    except Exception as e:
                        print(f"Error fetching {data_type} from {source_name}: {e}")
        
        return results
    
    def save_results(self, results: Dict[str, List[Any]], country_name: str):
        """
        Save results to JSON files, grouped by source
        
        Creates folder structure:
        output_dir/
          source1/
            country_countries.json
            country_attractions.json
          source2/
            country_countries.json
            ...
        
        Note: Sources that already save data in new structure (e.g., Wikivoyage)
        are skipped to avoid duplicate files.
        """
        # Sources that use new folder structure and don't need old JSON files
        sources_with_new_structure = ['wikivoyage', 'wikivoyage_en', 'wikivoyage_pl']
        
        for data_type, items in results.items():
            if not items:
                continue
            
            # Grupuj elementy według źródła
            grouped_by_source = group_by_source(items)
            
            # Zapisz do osobnych plików dla każdego źródła
            for source, source_items in grouped_by_source.items():
                # Skip sources that already save data in new structure
                if any(source.startswith(skip_source) for skip_source in sources_with_new_structure):
                    print(f"Skipping old JSON file creation for {source} (uses new folder structure)")
                    continue
                
                output_file = get_output_file_path(
                    self.output_dir,
                    source,
                    country_name,
                    data_type
                )
                
                # Wczytaj istniejące dane jeśli plik istnieje
                if output_file.exists():
                    with open(output_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                else:
                    existing_data = []
                
                # Dodaj nowe dane (unikaj duplikatów na podstawie source_url)
                existing_urls = {
                    item.get('source_url') 
                    for item in existing_data 
                    if item.get('source_url')
                }
                
                for item in source_items:
                    if item.get('source_url') not in existing_urls:
                        existing_data.append(item)
                        if item.get('source_url'):
                            existing_urls.add(item.get('source_url'))
                
                # Zapisz zaktualizowane dane
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(existing_data, f, indent=2, ensure_ascii=False, default=str)
                
                print(f"Saved {len(source_items)} {data_type} from {source} to {output_file}")
    
    async def run(self, country_name: str):
        """Run full data ingestion process"""
        print(f"Starting data ingestion for: {country_name}")
        print(f"Enabled sources: {', '.join(self.enabled_sources)}")
        
        results = await self.fetch_country_data(country_name)
        
        # Save results
        self.save_results(results, country_name)
        
        # Print summary
        print("\n=== Summary ===")
        for data_type, items in results.items():
            print(f"{data_type.capitalize()}: {len(items)} items")
        
        return results


async def main():
    """Main entry point"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python run_ingestion.py <country_name> [source1,source2,...]")
        print("Example: python run_ingestion.py 'France' 'wikipedia,wikidata'")
        sys.exit(1)
    
    country_name = sys.argv[1]
    enabled_sources = None
    
    if len(sys.argv) > 2:
        enabled_sources = sys.argv[2].split(",")
    
    orchestrator = DataIngestionOrchestrator(enabled_sources=enabled_sources)
    await orchestrator.run(country_name)


if __name__ == "__main__":
    asyncio.run(main())

