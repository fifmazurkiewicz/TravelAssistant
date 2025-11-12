"""
Wikivoyage fetcher using MediaWiki API
"""
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from .base_fetcher import BaseFetcher

try:
    import html2text
    HTML2TEXT_AVAILABLE = True
except ImportError:
    HTML2TEXT_AVAILABLE = False


class WikivoyageFetcher(BaseFetcher):
    """Fetcher for Wikivoyage data using MediaWiki API"""
    
    def __init__(self, language: str = "en", rate_limit_delay: float = 1.0, timeout: int = 30, output_dir = None, 
                 max_depth: int = 1, level_1_sections: Optional[List[str]] = None, level_2_sections: Optional[List[str]] = None):
        """
        Initialize Wikivoyage fetcher
        
        Args:
            language: Language code for Wikivoyage (en, pl, de, etc.). Default: en
            rate_limit_delay: Delay between requests in seconds
            timeout: Request timeout in seconds
            output_dir: Optional output directory for saving HTML files
            max_depth: How many levels deep to fetch (1 = country -> cities, 2 = country -> cities -> attractions). Default: 1
            level_1_sections: List of section names to extract links from at level 1 (e.g., ["Cities", "Cities and towns"]). Default: ["Cities", "Cities and towns"]
            level_2_sections: List of section names to extract links from at level 2 (e.g., ["See", "Do"]). Default: ["See", "Do"]
        """
        super().__init__(rate_limit_delay=rate_limit_delay, timeout=timeout, output_dir=output_dir)
        self.language = language
        self.max_depth = max_depth
        self.level_1_sections = level_1_sections or ["Cities", "Cities and towns"]
        self.level_2_sections = level_2_sections or ["See", "Do"]
        self.BASE_URL = f"https://{language}.wikivoyage.org/api/rest_v1"
    
    @property
    def source_name(self) -> str:
        return f"wikivoyage_{self.language}"
    
    def _generate_query_id(self, query: str) -> str:
        """
        Generuje unikalny identyfikator (hex hash) dla zapytania
        
        Args:
            query: Nazwa zapytania (np. 'Poland', 'Warsaw')
        
        Returns:
            Hex string (SHA256 hash pierwszych 16 bajtów)
        """
        query_normalized = query.lower().strip()
        hash_obj = hashlib.sha256(query_normalized.encode('utf-8'))
        return hash_obj.hexdigest()[:16]  # Pierwsze 16 znaków hex (32 bity)
    
    def _generate_unique_node_id(self, query_id: str) -> str:
        """
        Generuje unikalny ID node'a w formacie {source}_{query_id}
        
        Args:
            query_id: Query ID (hex hash)
        
        Returns:
            Unikalny ID node'a (np. 'wikivoyage_en_abc123')
        """
        source_normalized = self.source_name.lower().replace(" ", "_")
        return f"{source_normalized}_{query_id}"
    
    def _detect_node_type(self, query: str, parsed_data: Dict[str, Any]) -> str:
        """
        Wykrywa typ node'a na podstawie zawartości i struktury danych
        
        Args:
            query: Nazwa zapytania
            parsed_data: Sparsowane dane z HTML
        
        Returns:
            Typ node'a: 'country', 'city', 'region', 'destination', 'attraction'
        """
        metadata = parsed_data.get("metadata", {})
        sections = metadata.get("sections", {})
        
        # Jeśli ma sekcję "Regions" lub "Cities" → prawdopodobnie country
        if sections.get("regions") or sections.get("cities") or metadata.get("regions") or metadata.get("cities"):
            return "country"
        
        # Jeśli ma sekcję "Get in" (transport) → prawdopodobnie city/destination
        if sections.get("get_in") or sections.get("get_around"):
            # Sprawdź czy ma sekcje typowe dla miasta
            if sections.get("see") or sections.get("do") or sections.get("eat"):
                return "city"
            return "destination"
        
        # Jeśli jest w sekcji "Other destinations" → destination
        # (można sprawdzić przez parent_query w kontekście wywołania)
        
        # Jeśli ma współrzędne ale brak sekcji transportu → może być attraction
        if parsed_data.get("coordinates") and not sections.get("get_in"):
            return "attraction"
        
        # Sprawdź czy to może być region (jeśli ma sekcje typowe dla regionu)
        # Regiony często mają "Get in", "See", "Do" ale nie mają "Cities" lub "Regions"
        if sections.get("see") or sections.get("do"):
            # Jeśli nie ma "Cities" ani "Regions", ale ma "See" lub "Do" → może być region
            if not (sections.get("regions") or sections.get("cities") or metadata.get("regions") or metadata.get("cities")):
                return "region"
        
        # Domyślnie destination
        return "destination"
    
    def _detect_relationship_type(self, parent_type: str, child_type: str, section: str) -> str:
        """
        Wykrywa typ relacji na podstawie kontekstu
        
        Args:
            parent_type: Typ node'a rodzica (np. 'country', 'city')
            child_type: Typ node'a dziecka (np. 'city', 'region')
            section: Nazwa sekcji z której pochodzi link (np. 'Cities', 'Regions')
        
        Returns:
            Typ relacji: 'contains', 'located_in', 'part_of', 'related_to'
        """
        section_lower = section.lower()
        
        # Relacje hierarchiczne
        if section_lower in ["cities", "cities and towns", "municipalities"]:
            if parent_type == "country" and child_type == "city":
                return "contains"
            elif parent_type == "region" and child_type == "city":
                return "contains"
        
        if section_lower in ["regions", "subregions"]:
            if parent_type == "country" and child_type == "region":
                return "contains"
            elif parent_type == "region" and child_type == "region":
                return "part_of"
        
        if section_lower == "other destinations":
            return "contains"
        
        # Relacje geograficzne
        if parent_type == "country" and child_type in ["city", "region", "destination"]:
            return "contains"
        
        if child_type == "city" and parent_type == "country":
            return "located_in"
        
        # Domyślnie related_to
        return "related_to"
    
    async def fetch_country_info(self, country_name: str) -> List[Dict[str, Any]]:
        """Fetch country information from Wikivoyage"""
        results = []
        
        # Generate query ID for this main query
        main_query_id = self._generate_query_id(country_name)
        
        # Map country names based on language
        if self.language == "pl":
            country_mapping = {
                "France": "Francja",
                "Poland": "Polska",
                "Germany": "Niemcy",
                "Italy": "Włochy",
                "Spain": "Hiszpania",
                "United Kingdom": "Wielka Brytania",
                "United States": "Stany Zjednoczone",
                "Japan": "Japonia",
                "China": "Chiny",
                "India": "Indie",
            }
            page_name = country_mapping.get(country_name, country_name)
        else:
            # For English and other languages, use original name or URL-encode
            page_name = country_name.replace(" ", "_")
        
        # Get page summary
        summary_url = f"{self.BASE_URL}/page/summary/{page_name}"
        response = await self._make_request(summary_url)
        
        if response:
            data = response.json()
            country_data = {
                "name": data.get("title", country_name),
                "description": data.get("extract", ""),
                "source_url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            }
            results.append(self._add_source_metadata(country_data))
        
        # Get full page content
        content_url = f"{self.BASE_URL}/page/html/{page_name}"
        response = await self._make_request(content_url)
        
        if response:
            # Use advanced parser to extract all sections
            parsed_data = self._parse_wikivoyage_html(response.text, country_name)
            
            # Detect node type and generate unique node ID
            node_type = self._detect_node_type(country_name, parsed_data)
            unique_node_id = self._generate_unique_node_id(main_query_id)
            
            # Extract links from multiple sections for recursive fetching
            soup = BeautifulSoup(response.text, 'html.parser')
            # Try to find mw-parser-output - it can be in div or body
            # BeautifulSoup class_ can be a string or list, so we need to handle both
            main_content = soup.find("div", class_="mw-parser-output")
            if not main_content:
                # Try body with class
                main_content = soup.find("body", class_=lambda x: x and "mw-parser-output" in x)
            if not main_content:
                # Fallback: try to find body or main content area
                main_content = soup.find("body") or soup.find("main") or soup.find("div", id="content")
            
            if not main_content:
                print(f"WARNING: Could not find main_content for {country_name}")
            
            # Extract breadcrumbs for folder structure and parent relationships
            # Note: MediaWiki API /page/html endpoint typically does NOT include breadcrumbs.
            # Breadcrumbs are only in the full page HTML, so we always fetch full page HTML for breadcrumbs.
            breadcrumbs = self._extract_breadcrumbs(soup)
            
            # Always try to fetch full page HTML for breadcrumbs (API response usually doesn't have them)
            try:
                full_page_url = f"https://{self.language}.wikivoyage.org/wiki/{country_name.replace(' ', '_')}"
                full_page_response = await self._make_request(full_page_url)
                if full_page_response:
                    full_soup = BeautifulSoup(full_page_response.text, 'html.parser')
                    full_page_breadcrumbs = self._extract_breadcrumbs(full_soup)
                    if full_page_breadcrumbs:
                        breadcrumbs = full_page_breadcrumbs  # Use breadcrumbs from full page (more reliable)
            except Exception as e:
                print(f"WARNING: Error fetching full page HTML for breadcrumbs: {e}")
            
            breadcrumb_path = self._normalize_breadcrumb_path(breadcrumbs)
            
            # If breadcrumb_path is empty, try to infer hierarchy from known countries
            if not breadcrumb_path or not breadcrumb_path.strip():
                country_lower = country_name.lower()
                known_hierarchies = {
                    'poland': 'europe/central_europe/poland',
                    'france': 'europe/western_europe/france',
                    'germany': 'europe/central_europe/germany',
                    'spain': 'europe/southern_europe/spain',
                    'italy': 'europe/southern_europe/italy',
                }
                if country_lower in known_hierarchies:
                    breadcrumb_path = known_hierarchies[country_lower]
                else:
                    breadcrumb_path = None
            
            # Detect country from breadcrumbs and fetch drone laws
            detected_country = self._detect_country_from_breadcrumbs(breadcrumbs, country_name)
            if detected_country and self.output_dir:
                # Get country folder path
                from utils.file_manager import get_query_folder
                country_breadcrumb_path = None
                if breadcrumb_path:
                    # Extract country path from breadcrumb_path
                    # e.g., "europe/central_europe/poland" -> country is "poland"
                    path_parts = breadcrumb_path.split('/')
                    # Find country in path (usually last or second to last)
                    country_normalized = detected_country.lower().replace(" ", "_")
                    if country_normalized in path_parts:
                        # Get path up to and including country
                        country_index = path_parts.index(country_normalized)
                        country_breadcrumb_path = '/'.join(path_parts[:country_index + 1])
                
                if country_breadcrumb_path:
                    country_folder = get_query_folder(
                        self.output_dir,
                        self.source_name,
                        detected_country,
                        breadcrumb_path=country_breadcrumb_path
                    )
                    # Fetch drone laws for country
                    await self._fetch_drone_laws_for_country(detected_country, country_folder)
            
            # Prepare graph structure
            graph_nodes = []
            graph_edges = []
            
            # Create parent nodes from breadcrumbs (if any)
            if breadcrumbs and len(breadcrumbs) > 1:
                parent_node_ids = []  # Store parent node IDs to create edges between them
                
                # Skip the last breadcrumb (current page)
                for i, crumb in enumerate(breadcrumbs[:-1]):
                    parent_name = crumb.get("name", "")
                    parent_page_name = crumb.get("page_name", "")
                    if parent_name and parent_page_name:
                        # Generate IDs for parent nodes
                        parent_query_id = self._generate_query_id(parent_page_name)
                        parent_unique_node_id = self._generate_unique_node_id(parent_query_id)
                        parent_node_ids.append(parent_unique_node_id)
                        
                        # Create parent node (if not already in graph)
                        parent_exists = any(node.get("id") == parent_unique_node_id for node in graph_nodes)
                        if not parent_exists:
                            # Detect parent node type based on name and position
                            # If it's the last parent before current, check if it's a region or country
                            # For breadcrumbs like "Europe > Central Europe > Poland":
                            # - Europe: region
                            # - Central Europe: region (not country!)
                            # - Poland: country (current node, not in breadcrumbs)
                            parent_node_type = "region"  # Default to region
                            if i == len(breadcrumbs) - 2:  # Last parent before current
                                # Check if parent name suggests it's a country
                                parent_lower = parent_name.lower()
                                # Common country names in breadcrumbs (usually not in intermediate positions)
                                # But "Central Europe" is a region, not a country
                                if any(keyword in parent_lower for keyword in ["europe", "asia", "america", "africa", "oceania"]):
                                    parent_node_type = "region"
                                else:
                                    # Could be a country, but be conservative - use region unless we're sure
                                    parent_node_type = "region"
                            
                            parent_node = {
                                "id": parent_unique_node_id,
                                "name": parent_page_name.lower().replace(" ", "_"),
                                "type": parent_node_type,
                                "query_id": parent_query_id,
                                "query": parent_page_name,
                                "source": self.source_name,
                                "metadata": {
                                    "from_breadcrumb": True
                                }
                            }
                            graph_nodes.append(parent_node)
                        
                        # Create edge from previous parent to current parent (chain breadcrumbs)
                        if i > 0:
                            prev_parent_id = parent_node_ids[i - 1]
                            parent_chain_edge = {
                                "source": prev_parent_id,
                                "target": parent_unique_node_id,
                                "type": "contains",
                                "metadata": {
                                    "from_breadcrumb": True
                                }
                            }
                            graph_edges.append(parent_chain_edge)
                        
                        # Create edge from direct parent to current node
                        if i == len(breadcrumbs) - 2:  # Direct parent (last before current)
                            parent_edge = {
                                "source": parent_unique_node_id,
                                "target": unique_node_id,
                                "type": "contains",
                                "metadata": {
                                    "from_breadcrumb": True
                                }
                            }
                            graph_edges.append(parent_edge)
            
            # Create main node
            # Normalize name: lowercase and replace spaces with underscores
            country_name_normalized = country_name.lower().replace(" ", "_")
            main_node = {
                "id": unique_node_id,
                "name": country_name_normalized,
                "type": node_type,
                "query_id": main_query_id,
                "query": country_name,
                "source": self.source_name,
                "coordinates": parsed_data.get("coordinates"),
                "metadata": {
                    "sections": list(parsed_data.get("metadata", {}).get("sections", {}).keys()),
                    "languages": parsed_data.get("languages", []),
                    "source_url": results[0].get("source_url", "") if results else ""
                }
            }
            graph_nodes.append(main_node)
            
            if main_content:
                # Extract links from configured level 1 sections
                link_sections = {section: [] for section in self.level_1_sections}
                
                for section_name in self.level_1_sections:
                    links = self._extract_links_from_section(main_content, section_name)
                    link_sections[section_name] = links
                
                # Combine all links and remove duplicates
                all_links = []
                for section_name, links in link_sections.items():
                    all_links.extend(links)
                all_links = list(set(all_links))
                
                # Fetch linked pages recursively (depth from config)
                if all_links and self.output_dir:
                    child_nodes, child_edges = await self._fetch_linked_pages_recursive(
                        all_links, 
                        link_sections,
                        max_depth=self.max_depth,
                        visited=set(),
                        parent_query_id=main_query_id,
                        parent_query=country_name,
                        parent_node_id=unique_node_id,
                        parent_node_type=node_type,
                        parent_breadcrumb_path=breadcrumb_path
                    )
                    graph_nodes.extend(child_nodes)
                    graph_edges.extend(child_edges)
            
            # Save original HTML
            if self.output_dir:
                from utils.file_manager import save_html_file, save_markdown_file
                html_path = save_html_file(
                    self.output_dir,
                    self.source_name,
                    country_name,
                    response.text,
                    breadcrumb_path=breadcrumb_path
                )
                
                # Convert HTML to Markdown and save
                markdown_content = self._convert_html_to_markdown(soup)
                save_markdown_file(
                    self.output_dir,
                    self.source_name,
                    country_name,
                    markdown_content,
                    breadcrumb_path=breadcrumb_path
                )
            
            # Save main JSON file with all data (all sections in one file)
            if self.output_dir:
                from utils.file_manager import save_main_json, save_graph_structure, update_global_graph
                
                # Merge summary data with parsed data for main JSON
                main_data = parsed_data.copy()
                if results:
                    summary_data = results[0]
                    main_data.update({
                        "source_url": summary_data.get("source_url", ""),
                        "extract": summary_data.get("description", "")
                    })
                
                # Add query ID and Graph RAG metadata
                main_data["query_id"] = main_query_id
                main_data["query"] = country_name
                main_data["parent_query_id"] = None
                main_data["parent_query"] = None
                
                save_main_json(
                    self.output_dir,
                    self.source_name,
                    country_name,
                    main_data,
                    node_type=node_type,
                    unique_node_id=unique_node_id,
                    breadcrumb_path=breadcrumb_path
                )
                
                # Save graph structure (local graph.json)
                save_graph_structure(
                    self.output_dir,
                    self.source_name,
                    country_name,
                    graph_nodes,
                    graph_edges,
                    breadcrumb_path=breadcrumb_path
                )
                
                # Update global graph
                update_global_graph(
                    self.output_dir,
                    self.source_name,
                    graph_nodes,
                    graph_edges
                )
            
            if results:
                # Merge parsed data with summary data
                results[0].update(parsed_data)
            else:
                results.append(self._add_source_metadata(parsed_data))
        
        return results
    
    async def fetch_attractions(self, location: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch attractions from Wikivoyage"""
        results = []
        
        # Map location names based on language
        if self.language == "pl":
            location_mapping = {
                "Paris": "Paryż",
                "Warsaw": "Warszawa",
                "Berlin": "Berlin",
                "Rome": "Rzym",
                "Madrid": "Madryt",
                "London": "Londyn",
            }
            page_name = location_mapping.get(location, location)
        else:
            # For English and other languages, use original name or URL-encode
            page_name = location.replace(" ", "_")
        
        # Get page summary
        summary_url = f"{self.BASE_URL}/page/summary/{page_name}"
        response = await self._make_request(summary_url)
        
        if response:
            data = response.json()
            attraction_data = {
                "name": data.get("title", f"{location} Guide"),
                "location": location,
                "description": data.get("extract", ""),
                "source_url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            }
            results.append(self._add_source_metadata(attraction_data))
        
        # Get full page content for "Ciekawe miejsca" section
        content_url = f"{self.BASE_URL}/page/html/{page_name}"
        response = await self._make_request(content_url)
        
        if response:
            # Note: HTML is already saved in fetch_country_info with breadcrumbs
            # We don't need to save it again here to avoid duplicates
            soup = BeautifulSoup(response.text, 'html.parser')
            interesting_places = self._extract_interesting_places(soup)
            if interesting_places and results:
                results[0]["interesting_places"] = interesting_places
        
        return results
    
    def _extract_text_from_html(self, soup: BeautifulSoup) -> str:
        """Extract text content from HTML using BeautifulSoup"""
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        # Get main content
        main_content = soup.find("div", class_="mw-parser-output")
        if main_content:
            text = main_content.get_text()
        else:
            text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def _extract_sections(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract structured sections from Wikivoyage page"""
        sections = {}
        
        # Find all section headers (h2, h3)
        for heading in soup.find_all(["h2", "h3"]):
            heading_text = heading.get_text().strip()
            if not heading_text:
                continue
            
            # Get content after heading until next heading
            content_parts = []
            current = heading.next_sibling
            
            while current:
                if current.name in ["h2", "h3"]:
                    break
                if current.name == "p":
                    text = current.get_text().strip()
                    if text:
                        content_parts.append(text)
                elif current.name == "ul":
                    # List items
                    for li in current.find_all("li"):
                        text = li.get_text().strip()
                        if text:
                            content_parts.append(f"• {text}")
                current = current.next_sibling
            
            if content_parts:
                sections[heading_text] = "\n".join(content_parts)
        
        return sections
    
    def _extract_interesting_places(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract interesting places from 'Ciekawe miejsca' section"""
        places = []
        
        # Find "See" / "Ciekawe miejsca" section (language-dependent)
        see_keywords = {
            "pl": ["ciekawe miejsca", "atrakcje"],
            "en": ["see", "attractions", "sights"],
            "de": ["sehen", "attraktionen"],
        }
        keywords = see_keywords.get(self.language, ["see", "attractions"])
        
        for heading in soup.find_all(["h2", "h3"]):
            heading_text_lower = heading.get_text().lower()
            if any(keyword in heading_text_lower for keyword in keywords):
                # Get list items after this heading
                current = heading.next_sibling
                while current:
                    if current.name in ["h2", "h3"]:
                        break
                    if current.name == "ul":
                        for li in current.find_all("li"):
                            text = li.get_text().strip()
                            if text:
                                places.append({
                                    "name": text.split("—")[0].strip() if "—" in text else text,
                                    "description": text.split("—")[1].strip() if "—" in text else ""
                                })
                    current = current.next_sibling
                break
        
        return places
    
    def _parse_wikivoyage_html(self, html_content: str, country_name: str) -> Dict[str, Any]:
        """
        Parse Wikivoyage HTML using advanced parser to extract all sections
        
        This method extracts:
        - All sections (Beginning, Regions, Cities, Understand, Talk, Get in, etc.)
        - History with subsections
        - Languages
        - Coordinates
        - Structured metadata
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        # Try to find mw-parser-output - it can be in div or body
        # BeautifulSoup class_ can be a string or list, so we need to handle both
        main_content = soup.find("div", class_="mw-parser-output")
        if not main_content:
            # Try body with class (lambda function to handle class as list or string)
            main_content = soup.find("body", class_=lambda x: x and "mw-parser-output" in (x if isinstance(x, list) else [x]))
        if not main_content:
            # Fallback: try to find body or main content area
            main_content = soup.find("body") or soup.find("main") or soup.find("div", id="content")
        
        if not main_content:
            # Fallback to basic parsing
            return self._basic_parse(soup, country_name)
        
        # Extract coordinates
        coordinates = self._extract_coordinates(soup)
        
        # Extract all sections
        all_sections = self._extract_all_sections(main_content)
        
        # Extract basic description
        understand_content = all_sections.get("understand", "")
        description = understand_content.split('\n')[0] if understand_content else ""
        
        # Extract history
        history_sections = self._extract_history_sections(main_content)
        history_text = ""
        if history_sections:
            history_parts = []
            for section_name, section_content in history_sections.items():
                history_parts.append(f"{section_name}:\n{section_content}")
            history_text = "\n\n".join(history_parts)
        
        # Extract languages
        languages = self._extract_languages(main_content)
        if not languages:
            languages = []
        
        # Extract practical info
        get_in_content = all_sections.get("get_in", "")
        get_around_content = all_sections.get("get_around", "")
        practical_parts = []
        if get_in_content:
            practical_parts.append(f"Get in:\n{get_in_content}")
        if get_around_content:
            practical_parts.append(f"Get around:\n{get_around_content}")
        practical_info = "\n\n".join(practical_parts) if practical_parts else ""
        
        # Extract lists
        regions = self._extract_list_items(main_content, "Regions")
        cities = self._extract_list_items(main_content, "Cities")
        other_destinations = self._extract_list_items(main_content, "Other destinations")
        
        # Build result
        result = {
            "name": country_name,
            "description": description,
            "history": history_text,
            "practical_info": practical_info,
            "languages": languages,
            "coordinates": coordinates,
            "metadata": {
                "regions": regions,
                "cities": cities,
                "other_destinations": other_destinations,
                "sections": all_sections,
                "attractions": {
                    "see": all_sections.get("see", ""),
                    "do": all_sections.get("do", ""),
                },
                "dining": {
                    "eat": all_sections.get("eat", ""),
                    "drink": all_sections.get("drink", ""),
                },
                "accommodation": {
                    "sleep": all_sections.get("sleep", ""),
                },
                "shopping": {
                    "buy": all_sections.get("buy", ""),
                },
                "practical": {
                    "get_in": all_sections.get("get_in", ""),
                    "get_around": all_sections.get("get_around", ""),
                    "stay_safe": all_sections.get("stay_safe", ""),
                    "stay_healthy": all_sections.get("stay_healthy", ""),
                    "respect": all_sections.get("respect", ""),
                    "connect": all_sections.get("connect", ""),
                },
                "other": {
                    "learn": all_sections.get("learn", ""),
                    "work": all_sections.get("work", ""),
                }
            }
        }
        
        return result
    
    def _basic_parse(self, soup: BeautifulSoup, country_name: str) -> Dict[str, Any]:
        """Fallback basic parsing if advanced parser fails"""
        text_content = self._extract_text_from_html(soup)
        sections = self._extract_sections(soup)
        
        return {
            "name": country_name,
            "description": text_content[:500] if text_content else "",
            "full_content": text_content,
            "sections": sections,
        }
    
    def _extract_coordinates(self, soup: BeautifulSoup) -> Dict[str, float] | None:
        """Extract coordinates from JavaScript in HTML"""
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'wgCoordinates' in script.string:
                match = re.search(r'"wgCoordinates":\{"lat":([\d.]+),"lon":([\d.]+)\}', script.string)
                if match:
                    return {
                        "lat": float(match.group(1)),
                        "lon": float(match.group(2))
                    }
        return None
    
    def _extract_all_sections(self, main_content) -> Dict[str, str]:
        """Extract all sections from Wikivoyage guide"""
        sections = {}
        
        section_names = [
            "Beginning", "Regions", "Cities", "Other destinations",
            "Understand", "Talk", "Get in", "Get around",
            "See", "Do", "Buy", "Eat", "Drink", "Sleep",
            "Learn", "Work", "Stay safe", "Stay healthy",
            "Respect", "Connect"
        ]
        
        for section_name in section_names:
            content = self._extract_section_content(main_content, section_name)
            if content:
                sections[section_name.lower().replace(" ", "_")] = content
        
        return sections
    
    def _extract_section_content(self, main_content, section_title: str) -> str:
        """Extract content of a section"""
        # First, try to find section by heading ID (Wikivoyage uses id attributes)
        section_id = section_title.lower().replace(" ", "_")
        heading = main_content.find(['h2', 'h3', 'h4'], id=section_id)
        
        # If not found by ID, search by text
        if not heading:
            for h in main_content.find_all(['h2', 'h3', 'h4']):
                heading_text = h.get_text().strip()
                if section_title.lower() in heading_text.lower():
                    heading = h
                    break
        
        if not heading:
            return ""
        
        # Try to find parent <section> tag (Wikivoyage structure)
        section_tag = heading.find_parent('section')
        if section_tag:
            # Extract all text from the section
            content_parts = []
            for elem in section_tag.find_all(['p', 'ul', 'ol', 'dl']):
                if elem.name == 'p':
                    text = elem.get_text().strip()
                    if text:
                        content_parts.append(text)
                elif elem.name in ['ul', 'ol']:
                    for li in elem.find_all('li', recursive=False):
                        text = li.get_text().strip()
                        if text:
                            content_parts.append(f"• {text}")
                elif elem.name == 'dl':
                    for dt in elem.find_all('dt', recursive=False):
                        term = dt.get_text().strip()
                        dd = dt.find_next_sibling('dd')
                        if dd:
                            definition = dd.get_text().strip()
                            content_parts.append(f"{term}: {definition}")
            return "\n".join(content_parts)
        
        # Fallback: extract using next_sibling approach
        content_parts = []
        current = heading.next_sibling
        heading_level = int(heading.name[1]) if heading.name.startswith('h') else 2
        
        while current:
            if current.name and current.name.startswith('h'):
                current_level = int(current.name[1])
                if current_level <= heading_level:
                    break
            
            if current.name == 'p':
                text = current.get_text().strip()
                if text:
                    content_parts.append(text)
            elif current.name == 'ul':
                for li in current.find_all('li', recursive=False):
                    text = li.get_text().strip()
                    if text:
                        content_parts.append(f"• {text}")
            elif current.name == 'dl':
                for dt in current.find_all('dt', recursive=False):
                    term = dt.get_text().strip()
                    dd = dt.find_next_sibling('dd')
                    if dd:
                        definition = dd.get_text().strip()
                        content_parts.append(f"{term}: {definition}")
            
            current = current.next_sibling
        
        return "\n".join(content_parts)
    
    def _extract_list_items(self, main_content, section_title: str) -> List[str]:
        """Extract list items from a section"""
        heading = None
        for h in main_content.find_all(['h2', 'h3', 'h4']):
            heading_text = h.get_text().strip()
            if section_title.lower() in heading_text.lower():
                heading = h
                break
        
        if not heading:
            return []
        
        items = []
        current = heading.next_sibling
        heading_level = int(heading.name[1]) if heading.name.startswith('h') else 2
        
        while current:
            if current.name and current.name.startswith('h'):
                level = int(current.name[1])
                if level <= heading_level:
                    break
            
            if current.name == 'ul':
                for li in current.find_all('li', recursive=False):
                    text = li.get_text().strip()
                    text = re.sub(r'\s*\([^)]*\)\s*$', '', text)
                    if text:
                        items.append(text)
            
            current = current.next_sibling
        
        return items
    
    def _extract_history_sections(self, main_content) -> Dict[str, str]:
        """Extract history subsections"""
        history_sections = {}
        
        history_heading = None
        for h in main_content.find_all(['h2', 'h3']):
            if h.get_text().strip().lower() == 'history':
                history_heading = h
                break
        
        if not history_heading:
            return history_sections
        
        current = history_heading.next_sibling
        history_level = int(history_heading.name[1])
        current_subsection = None
        current_content = []
        
        while current:
            if current.name and current.name.startswith('h'):
                level = int(current.name[1])
                if level > history_level:
                    if current_subsection and current_content:
                        history_sections[current_subsection] = "\n".join(current_content)
                    current_subsection = current.get_text().strip()
                    current_content = []
                elif level <= history_level:
                    if current_subsection and current_content:
                        history_sections[current_subsection] = "\n".join(current_content)
                    break
            elif current.name == 'p' and current_subsection:
                text = current.get_text().strip()
                if text:
                    current_content.append(text)
            elif current.name == 'ul' and current_subsection:
                for li in current.find_all('li', recursive=False):
                    text = li.get_text().strip()
                    if text:
                        current_content.append(f"• {text}")
            
            current = current.next_sibling
        
        if current_subsection and current_content:
            history_sections[current_subsection] = "\n".join(current_content)
        
        return history_sections
    
    def _extract_links_from_section(self, main_content, section_title: str) -> List[str]:
        """
        Extract Wikivoyage page links from a section (e.g., Cities, Municipalities)
        
        Args:
            main_content: BeautifulSoup element containing main content
            section_title: Title of the section to extract links from
        
        Returns:
            List of page names (without namespace, ready for API calls)
        """
        links = []
        
        # Find the section heading - try multiple methods
        heading = None
        
        # Method 1: Try exact ID match (case-insensitive)
        section_id = section_title.lower().replace(" ", "_")
        for h in main_content.find_all(['h2', 'h3', 'h4']):
            h_id = h.get('id', '').lower()
            if h_id == section_id:
                heading = h
                break
        
        # Method 2: Try text match in heading (exact match or starts with section title followed by space/punctuation)
        if not heading:
            for h in main_content.find_all(['h2', 'h3', 'h4']):
                heading_text = h.get_text().strip()
                heading_lower = heading_text.lower()
                section_lower = section_title.lower()
                # Exact match or starts with section title followed by space, colon, or end of string
                if (heading_lower == section_lower or 
                    (heading_lower.startswith(section_lower) and 
                     (len(heading_lower) == len(section_lower) or 
                      heading_lower[len(section_lower)] in [' ', ':', '\n', '\t']))):
                    heading = h
                    break
        
        if not heading:
            return links
        
        # Try to find parent <section> tag
        section_tag = heading.find_parent('section')
        if section_tag:
            # Find all links in the section (including nested in tables, divs, etc.)
            all_links_in_section = section_tag.find_all('a', href=True)
            
            for link in all_links_in_section:
                href = link.get('href', '')
                # Filter Wikivoyage internal links (format: ./PageName or /wiki/PageName)
                if href.startswith('./') or '/wiki/' in href:
                    # Extract page name
                    if href.startswith('./'):
                        page_name = href[2:]  # Remove './'
                    else:
                        # Extract from /wiki/PageName
                        page_name = href.split('/wiki/')[-1] if '/wiki/' in href else None
                    
                    if page_name:
                        # Remove anchors and query params
                        page_name = page_name.split('#')[0].split('?')[0]
                        # Skip special pages, categories, files, etc.
                        if not any(page_name.startswith(prefix) for prefix in ['Category:', 'File:', 'Template:', 'Special:', 'Help:', 'User:']):
                            # Skip [edit] links and empty text
                            link_text = link.get_text().strip()
                            if link_text and link_text.lower() != '[edit]' and link_text:
                                # Check if link has rel="mw:WikiLink" (internal Wikivoyage link)
                                link_rel = link.get('rel', '')
                                if link_rel == 'mw:WikiLink' or (isinstance(link_rel, list) and 'mw:WikiLink' in link_rel) or (isinstance(link_rel, str) and 'mw:WikiLink' in link_rel):
                                    links.append(page_name)
                                # Also include if it's a direct link (no rel attribute or just href)
                                elif not link_rel or link_rel == []:
                                    links.append(page_name)
        else:
            # Fallback: search in content after heading until next same-level heading
            current = heading.next_sibling
            heading_level = int(heading.name[1]) if heading.name.startswith('h') else 2
            
            while current:
                if current.name and current.name.startswith('h'):
                    current_level = int(current.name[1])
                    if current_level <= heading_level:
                        break
                
                # Find links in lists, tables, divs, paragraphs
                if current.name in ['ul', 'ol', 'table', 'div', 'p']:
                    for link in current.find_all('a', href=True):
                        href = link.get('href', '')
                        if href.startswith('./') or '/wiki/' in href:
                            if href.startswith('./'):
                                page_name = href[2:]
                            else:
                                page_name = href.split('/wiki/')[-1] if '/wiki/' in href else None
                            
                            if page_name:
                                page_name = page_name.split('#')[0].split('?')[0]
                                if not any(page_name.startswith(prefix) for prefix in ['Category:', 'File:', 'Template:', 'Special:', 'Help:', 'User:']):
                                    link_text = link.get_text().strip()
                                    if link_text and link_text.lower() != '[edit]' and link_text:
                                        # Check if link has rel="mw:WikiLink"
                                        link_rel = link.get('rel', '')
                                        if link_rel == 'mw:WikiLink' or (isinstance(link_rel, list) and 'mw:WikiLink' in link_rel) or (isinstance(link_rel, str) and 'mw:WikiLink' in link_rel):
                                            links.append(page_name)
                                        elif not link_rel or link_rel == []:
                                            links.append(page_name)
                
                current = current.next_sibling
        
        # Remove duplicates while preserving order
        seen = set()
        unique_links = []
        for link in links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)
        
        return unique_links
    
    def _extract_breadcrumbs(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extract breadcrumbs from Wikivoyage HTML page
        
        Breadcrumbs are in: <div id="contentSub"><div id="mw-content-subtitle"><span class="ext-geocrumbs-breadcrumbs">
        Format: Europe > Central Europe > Poland
        
        Args:
            soup: BeautifulSoup object of the HTML page
        
        Returns:
            List of breadcrumb items with 'name' and 'url' (if available)
            Example: [
                {"name": "Europe", "url": "/wiki/Europe", "page_name": "Europe"},
                {"name": "Central Europe", "url": "/wiki/Central_Europe", "page_name": "Central_Europe"},
                {"name": "Poland", "url": None, "page_name": None}  # Current page has no URL
            ]
        """
        breadcrumbs = []
        
        # Find breadcrumbs container - try multiple methods
        breadcrumbs_span = None
        
        # Method 1: Look in contentSub > mw-content-subtitle > ext-geocrumbs-breadcrumbs
        content_sub = soup.find("div", id="contentSub")
        if content_sub:
            mw_content_subtitle = content_sub.find("div", id="mw-content-subtitle")
            if mw_content_subtitle:
                breadcrumbs_span = mw_content_subtitle.find("span", class_="ext-geocrumbs-breadcrumbs")
                if not breadcrumbs_span:
                    breadcrumbs_span = mw_content_subtitle.find("span", class_=lambda x: x and "breadcrumb" in str(x).lower())
        
        # Method 2: Look directly for mw-content-subtitle
        if not breadcrumbs_span:
            mw_content_subtitle = soup.find("div", id="mw-content-subtitle")
            if mw_content_subtitle:
                breadcrumbs_span = mw_content_subtitle.find("span", class_="ext-geocrumbs-breadcrumbs")
                if not breadcrumbs_span:
                    breadcrumbs_span = mw_content_subtitle.find("span", class_=lambda x: x and "breadcrumb" in str(x).lower())
        
        # Method 3: Look for any span with breadcrumb class
        if not breadcrumbs_span:
            breadcrumbs_span = soup.find("span", class_="ext-geocrumbs-breadcrumbs")
            if not breadcrumbs_span:
                breadcrumbs_span = soup.find("span", class_=lambda x: x and "breadcrumb" in str(x).lower())
        
        # Method 4: Fallback - try to find any element containing breadcrumb text
        if not breadcrumbs_span:
            all_spans = soup.find_all("span")
            for span in all_spans:
                span_text = span.get_text()
                if ">" in span_text and any(keyword in span_text.lower() for keyword in ["europe", "asia", "america", "africa"]):
                    breadcrumbs_span = span
                    break
        
        if not breadcrumbs_span:
            return breadcrumbs
        
        # Extract all links and text from breadcrumbs
        # Format: <bdi><a href="/wiki/Europe" title="Europe">Europe</a></bdi> &gt; <bdi><a href="/wiki/Central_Europe" title="Central Europe">Central Europe</a></bdi> &gt; <bdi>Poland</bdi>
        # Structure: Each breadcrumb is in a <bdi> tag, links are nested inside <bdi><a>
        # We need to iterate through <bdi> elements, not <a> elements directly
        
        # Find all <bdi> elements in breadcrumbs span
        bdi_elements = breadcrumbs_span.find_all('bdi', recursive=False)  # Only direct children
        if not bdi_elements:
            bdi_elements = breadcrumbs_span.find_all('bdi')
        
        for bdi_element in bdi_elements:
            # Check if bdi contains a link
            link = bdi_element.find('a')
            if link:
                # This is a link breadcrumb (e.g., Europe, Central Europe)
                href = link.get('href', '')
                title = link.get('title', '')
                name = link.get_text().strip()
                
                if name and name not in ['>', '&gt;']:  # Skip separators
                    # Extract page name from href (e.g., /wiki/Europe -> Europe, /wiki/Central_Europe -> Central_Europe)
                    page_name = None
                    if href:
                        if '/wiki/' in href:
                            page_name = href.split('/wiki/')[-1].split('#')[0].split('?')[0]
                        elif href.startswith('./'):
                            page_name = href[2:].split('#')[0].split('?')[0]
                    
                    # Use title attribute if available, otherwise use page_name from URL, otherwise use displayed name
                    final_name = title or (page_name.replace('_', ' ') if page_name else name)
                    
                    breadcrumbs.append({
                        "name": final_name,
                        "url": href,
                        "page_name": page_name or final_name.replace(' ', '_')
                    })
            else:
                # This is text breadcrumb (current page, no link) - e.g., <bdi>Poland</bdi>
                name = bdi_element.get_text().strip()
                if name and name not in ['>', '&gt;', '']:  # Skip separators and empty
                    breadcrumbs.append({
                        "name": name,
                        "url": None,
                        "page_name": None
                    })
        
        return breadcrumbs
    
    def _normalize_breadcrumb_path(self, breadcrumbs: List[Dict[str, str]]) -> str:
        """
        Normalize breadcrumbs to a folder path
        
        Args:
            breadcrumbs: List of breadcrumb items (includes current page as last item)
        
        Returns:
            Normalized path string (e.g., "europe/central_europe/poland")
            Returns empty string if no breadcrumbs found
        """
        if not breadcrumbs:
            return ""
        
        path_parts = []
        for crumb in breadcrumbs:
            name = crumb.get("name", "")
            if name:
                # Normalize: lowercase, replace spaces with underscores, remove special chars
                normalized = name.lower().replace(" ", "_")
                # Remove special characters that might cause issues in file paths
                normalized = "".join(c for c in normalized if c.isalnum() or c in ['_', '-'])
                if normalized:  # Only add if normalized name is not empty
                    path_parts.append(normalized)
        
        if not path_parts:
            return ""
        
        return "/".join(path_parts)
    
    def _detect_country_from_breadcrumbs(self, breadcrumbs: List[Dict[str, str]], current_query: str) -> Optional[str]:
        """
        Detect country name from breadcrumbs
        
        Args:
            breadcrumbs: List of breadcrumb items
            current_query: Current query name (e.g., "Krakow", "Warsaw")
        
        Returns:
            Country name if detected, None otherwise
        
        Examples:
            breadcrumbs = [{"name": "Europe"}, {"name": "Central Europe"}, {"name": "Poland"}]
            current_query = "Krakow"
            -> Returns "Poland"
            
            breadcrumbs = [{"name": "Europe"}, {"name": "Central Europe"}, {"name": "Poland"}, {"name": "Mazowieckie"}]
            current_query = "Warsaw"
            -> Returns "Poland" (not "Mazowieckie", which is a voivodeship/region)
        """
        if not breadcrumbs or len(breadcrumbs) < 2:
            return None
        
        # List of known region names (not countries) - continents, subcontinents, etc.
        region_keywords = [
            "europe", "asia", "america", "africa", "oceania",
            "central europe", "western europe", "eastern europe", "southern europe", "northern europe",
            "southeast asia", "east asia", "south asia", "central asia", "middle east",
            "north america", "south america", "central america", "caribbean",
            "east africa", "west africa", "southern africa", "north africa"
        ]
        
        # Get all breadcrumb names (excluding current page)
        breadcrumb_names = [crumb.get("name", "") for crumb in breadcrumbs[:-1] if crumb.get("name")]
        
        if not breadcrumb_names:
            return None
        
        def is_administrative_region(name: str) -> bool:
            """
            Check if a breadcrumb name looks like an administrative region
            (voivodeship, state, province, etc.) rather than a country
            
            Heuristics:
            - Ends with typical administrative region suffixes
            - Contains words like "voivodeship", "state", "province", "oblast"
            - Polish voivodeships often end with "-skie", "-ckie", "-skie"
            """
            name_lower = name.lower()
            
            # Check for explicit administrative region keywords
            admin_keywords = [
                "voivodeship", "voivodship", "oblast", "state", "province", "region",
                "county", "prefecture", "governorate", "autonomous region"
            ]
            if any(keyword in name_lower for keyword in admin_keywords):
                return True
            
            # Polish voivodeship suffixes (common patterns)
            polish_suffixes = ["skie", "ckie", "zkie"]
            if any(name_lower.endswith(suffix) for suffix in polish_suffixes):
                # But exclude if it's a known country name that happens to end with these
                # (unlikely, but be safe)
                return True
            
            # Check for compound names that look like regions (e.g., "Lower Silesian", "Greater Poland")
            if any(word in name_lower for word in ["lower", "upper", "greater", "lesser", "north", "south", "east", "west"]):
                # If it's not a continent/subcontinent, it might be an administrative region
                if not any(keyword in name_lower for keyword in region_keywords):
                    return True
            
            return False
        
        # Start from the last breadcrumb (most specific) and go backwards
        for i in range(len(breadcrumb_names) - 1, -1, -1):
            name = breadcrumb_names[i].lower()
            
            # Skip if it's a known region (continent/subcontinent)
            if any(keyword in name for keyword in region_keywords):
                continue
            
            # Skip if it looks like an administrative region
            if is_administrative_region(breadcrumb_names[i]):
                continue
            
            # This is likely a country (not a continent, not an administrative region)
            # Return the first non-region breadcrumb we find going backwards
            return breadcrumb_names[i]
        
        # If no country found, return None
        return None
    
    async def _fetch_drone_laws_for_country(self, country_name: str, country_folder_path: Path) -> None:
        """
        Fetch drone laws data for a country and save to drone_laws source
        
        Args:
            country_name: Name of the country (e.g., "Poland")
            country_folder_path: Path to country folder (not used, kept for compatibility)
        """
        if not self.output_dir:
            return
        
        try:
            # Import fetchers
            from .drone_laws_fetcher import DroneLawsFetcher
            from .drone_made_fetcher import DroneMadeFetcher
            
            # Initialize fetchers
            drone_laws_fetcher = DroneLawsFetcher(
                rate_limit_delay=self.rate_limit_delay,
                timeout=self.timeout,
                output_dir=self.output_dir
            )
            drone_made_fetcher = DroneMadeFetcher(
                rate_limit_delay=self.rate_limit_delay,
                timeout=self.timeout,
                output_dir=self.output_dir
            )
            
            # Fetch data from both sources
            async with drone_laws_fetcher:
                drone_laws_results = await drone_laws_fetcher.fetch_country_info(country_name)
                if drone_laws_results:
                    # Save markdown to drone_laws source
                    markdown_content = drone_laws_results[0].get("description", "")
                    if markdown_content:
                        drone_laws_fetcher.save_markdown_to_source(country_name, markdown_content)
            
            async with drone_made_fetcher:
                # Fetch HTML directly
                country_normalized = drone_made_fetcher._normalize_country_name(country_name)
                url = f"{drone_made_fetcher.BASE_URL}/post/{country_normalized}"
                response = await drone_made_fetcher._make_request(url)
                if response:
                    drone_made_fetcher.save_html_and_text_to_source(country_name, response.text)
        
        except Exception as e:
            print(f"WARNING: Error fetching drone laws for {country_name}: {e}")
    
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
        
        # Find main content area (mw-parser-output is MediaWiki's main content div)
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
    
    async def _fetch_linked_pages_recursive(
        self, 
        page_names: List[str],
        link_sections: Dict[str, List[str]],  # Mapowanie sekcji do linków
        max_depth: int = 1, 
        current_depth: int = 0,
        visited: set = None,
        parent_query_id: str = None,
        parent_query: str = None,
        parent_node_id: str = None,
        parent_node_type: str = None,
        parent_breadcrumb_path: Optional[str] = None
    ) -> tuple:
        """
        Recursively fetch linked pages and save their HTML and JSON
        
        Args:
            page_names: List of page names to fetch
            link_sections: Dictionary mapping section names to lists of page names
            max_depth: Maximum recursion depth (default: 1 for one layer)
            current_depth: Current recursion depth
            visited: Set of already visited pages to avoid duplicates
            parent_query_id: Query ID of parent node
            parent_query: Query name of parent node
            parent_node_id: Unique node ID of parent
            parent_node_type: Node type of parent
        
        Returns:
            Tuple of (nodes, edges) for Graph RAG
        """
        if visited is None:
            visited = set()
        
        nodes = []
        edges = []
        
        if current_depth >= max_depth:
            return nodes, edges
        
        for page_name in page_names:
            # Normalize page name
            page_name_normalized = page_name.replace(" ", "_")
            
            # Skip if already visited
            if page_name_normalized in visited:
                continue
            
            visited.add(page_name_normalized)
            
            try:
                # Fetch page HTML
                content_url = f"{self.BASE_URL}/page/html/{page_name_normalized}"
                response = await self._make_request(content_url)
                
                if not response:
                    continue
                
                # Parse HTML to extract breadcrumbs
                soup = BeautifulSoup(response.text, 'html.parser')
                child_breadcrumbs = self._extract_breadcrumbs(soup)
                
                # If no breadcrumbs found for child, try fetching full page HTML
                if not child_breadcrumbs:
                    try:
                        full_page_url = f"https://{self.language}.wikivoyage.org/wiki/{page_name_normalized}"
                        full_page_response = await self._make_request(full_page_url)
                        if full_page_response:
                            full_soup = BeautifulSoup(full_page_response.text, 'html.parser')
                            child_breadcrumbs = self._extract_breadcrumbs(full_soup)
                    except Exception:
                        pass
                
                child_breadcrumb_path = self._normalize_breadcrumb_path(child_breadcrumbs)
                
                # If child breadcrumbs are empty, use parent breadcrumb path + child name
                if not child_breadcrumb_path or not child_breadcrumb_path.strip():
                    if parent_breadcrumb_path and parent_breadcrumb_path.strip():
                        # Append child name to parent breadcrumb path
                        child_name_normalized = page_name_normalized.lower().replace(" ", "_")
                        child_breadcrumb_path = f"{parent_breadcrumb_path}/{child_name_normalized}"
                
                # Save HTML
                if self.output_dir:
                    from utils.file_manager import save_html_file, save_main_json, save_markdown_file
                    save_html_file(
                        self.output_dir,
                        self.source_name,
                        page_name_normalized,  # Use page name as query
                        response.text,
                        breadcrumb_path=child_breadcrumb_path
                    )
                    
                    # Convert HTML to Markdown and save
                    child_markdown_content = self._convert_html_to_markdown(soup)
                    save_markdown_file(
                        self.output_dir,
                        self.source_name,
                        page_name_normalized,
                        child_markdown_content,
                        breadcrumb_path=child_breadcrumb_path
                    )
                
                # Parse and save sections
                parsed_data = self._parse_wikivoyage_html(response.text, page_name_normalized)
                
                # Detect node type and generate IDs
                child_query_id = self._generate_query_id(page_name_normalized)
                child_node_type = self._detect_node_type(page_name_normalized, parsed_data)
                child_unique_node_id = self._generate_unique_node_id(child_query_id)
                
                # Find which section this page came from
                source_section = None
                for section_name, links in link_sections.items():
                    if page_name in links or page_name_normalized in links:
                        source_section = section_name
                        break
                
                # Detect relationship type
                relationship_type = self._detect_relationship_type(
                    parent_node_type or "country",
                    child_node_type,
                    source_section or "Cities"
                )
                
                # Create child node
                # Normalize name: lowercase and replace spaces with underscores
                child_name_normalized = page_name_normalized.lower().replace(" ", "_")
                child_node = {
                    "id": child_unique_node_id,
                    "name": child_name_normalized,
                    "type": child_node_type,
                    "query_id": child_query_id,
                    "query": page_name_normalized,  # Keep original query name
                    "source": self.source_name,
                    "coordinates": parsed_data.get("coordinates"),
                    "metadata": {
                        "sections": list(parsed_data.get("metadata", {}).get("sections", {}).keys()),
                        "languages": parsed_data.get("languages", []),
                    }
                }
                nodes.append(child_node)
                
                # Create edge from parent to child
                if parent_node_id:
                    edge = {
                        "source": parent_node_id,
                        "target": child_unique_node_id,
                        "type": relationship_type,
                        "metadata": {
                            "parent_query": parent_query,
                            "child_query": page_name_normalized,
                            "parent_query_id": parent_query_id,
                            "child_query_id": child_query_id,
                            "section": source_section or "Cities"
                        }
                    }
                    edges.append(edge)
                
                # Save main JSON file with all data (query.json) - wszystkie sekcje w jednym pliku
                if self.output_dir:
                    from utils.file_manager import save_main_json, save_graph_structure
                    # Save main JSON file with all data (query.json)
                    main_data = parsed_data.copy()
                    main_data["query_id"] = child_query_id
                    main_data["query"] = page_name_normalized
                    main_data["parent_query_id"] = parent_query_id
                    main_data["parent_query"] = parent_query
                    save_main_json(
                        self.output_dir,
                        self.source_name,
                        page_name_normalized,
                        main_data,
                        node_type=child_node_type,
                        unique_node_id=child_unique_node_id,
                        breadcrumb_path=child_breadcrumb_path
                    )
                    
                # Recursively fetch children of this child (e.g., Warsaw -> Łazienki Królewskie from "See" section)
                child_local_nodes = [child_node]
                child_local_edges = []
                
                if current_depth < max_depth - 1:
                    # Parse HTML to find links in child's page
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # Try to find mw-parser-output - it can be in div or body
                    # BeautifulSoup class_ can be a string or list, so we need to handle both
                    child_main_content = soup.find("div", class_="mw-parser-output")
                    if not child_main_content:
                        # Try body with class (lambda function to handle class as list or string)
                        child_main_content = soup.find("body", class_=lambda x: x and "mw-parser-output" in (x if isinstance(x, list) else [x]))
                    if not child_main_content:
                        # Fallback: try to find body or main content area
                        child_main_content = soup.find("body") or soup.find("main") or soup.find("div", id="content")
                    
                    if child_main_content:
                        # Extract links from configured level 2 sections
                        child_link_sections = {section: [] for section in self.level_2_sections}
                        
                        for section_name in self.level_2_sections:
                            child_links = self._extract_links_from_section(child_main_content, section_name)
                            child_link_sections[section_name] = child_links
                        
                        # Combine all child links
                        child_all_links = []
                        for section_name, links in child_link_sections.items():
                            child_all_links.extend(links)
                        
                        # Remove duplicates
                        child_all_links = list(set(child_all_links))
                        
                        if child_all_links:
                            # Recursively fetch grandchildren (attractions)
                            grandchild_nodes, grandchild_edges = await self._fetch_linked_pages_recursive(
                                child_all_links,
                                child_link_sections,
                                max_depth,
                                current_depth + 1,
                                visited,
                                parent_query_id=child_query_id,
                                parent_query=page_name_normalized,
                                parent_node_id=child_unique_node_id,
                                parent_node_type=child_node_type,
                                parent_breadcrumb_path=child_breadcrumb_path
                            )
                            nodes.extend(grandchild_nodes)
                            edges.extend(grandchild_edges)
                            
                            # Add grandchildren to child's local graph
                            child_local_nodes.extend(grandchild_nodes)
                            child_local_edges.extend(grandchild_edges)
                
                # Save local graph for this child query (includes its children if any)
                if self.output_dir:
                    from utils.file_manager import save_graph_structure
                    save_graph_structure(
                        self.output_dir,
                        self.source_name,
                        page_name_normalized,
                        child_local_nodes,
                        child_local_edges,
                        breadcrumb_path=child_breadcrumb_path
                    )
                
            except Exception as e:
                print(f"WARNING: Error fetching page {page_name_normalized}: {e}")
                continue
        
        return nodes, edges
    
    def _extract_languages(self, main_content) -> List[str]:
        """Extract languages from Talk section"""
        talk_content = self._extract_section_content(main_content, "Talk")
        languages = []
        
        if 'polish' in talk_content.lower():
            languages.append("Polish")
        if 'english' in talk_content.lower():
            languages.append("English")
        
        language_patterns = [
            r'([A-Z][a-z]+)\s+is\s+(?:the\s+)?(?:official\s+)?language',
            r'languages?:\s*([A-Z][a-z]+(?:\s*,\s*[A-Z][a-z]+)*)',
        ]
        
        for pattern in language_patterns:
            matches = re.findall(pattern, talk_content)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                langs = [l.strip() for l in match.split(',')]
                languages.extend(langs)
        
        return sorted(list(set(languages)))

