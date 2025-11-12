"""
Narzędzia do zarządzania plikami dla różnych źródeł danych
"""
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_source_folder(output_dir: Path, source: str) -> Path:
    """
    Zwraca ścieżkę do folderu dla danego źródła
    
    Args:
        output_dir: Główny katalog wyjściowy
        source: Nazwa źródła (np. 'wikivoyage_en', 'wikidata', 'wikipedia')
    
    Returns:
        Path do folderu źródła
    """
    # Normalizuj nazwę źródła (usuń sufiksy językowe, zamień na małe litery)
    source_normalized = source.lower()
    
    # Mapowanie źródeł do nazw folderów
    source_mapping = {
        'wikivoyage_en': 'wikivoyage',
        'wikivoyage_pl': 'wikivoyage',
        'wikivoyage': 'wikivoyage',
        'wikidata': 'wikidata',
        'wikipedia': 'wikipedia',
        'tripadvisor': 'tripadvisor',
        'lonely_planet': 'lonely_planet',
        'world_travel_guide': 'world_travel_guide',
        'travel_independent': 'travel_independent',
    }
    
    # Użyj mapowania lub nazwy źródła jako nazwy folderu
    folder_name = source_mapping.get(source_normalized, source_normalized)
    
    source_folder = output_dir / folder_name
    source_folder.mkdir(parents=True, exist_ok=True)
    
    return source_folder


def get_query_folder(output_dir: Path, source: str, query: str, breadcrumb_path: Optional[str] = None) -> Path:
    """
    Zwraca ścieżkę do folderu dla danego query (np. poland) w źródle
    
    Jeśli breadcrumb_path jest podane, używa go do tworzenia hierarchicznej struktury folderów.
    Struktura z breadcrumbs: output_dir/source/breadcrumb_path/
    Przykład: data_ingestion_output/wikivoyage/europe/central_europe/poland/
    
    Struktura bez breadcrumbs: output_dir/source/query/
    Przykład: data_ingestion_output/wikivoyage/poland/
    
    Args:
        output_dir: Główny katalog wyjściowy
        source: Nazwa źródła
        query: Nazwa query (np. 'poland', 'warsaw')
        breadcrumb_path: Opcjonalna ścieżka breadcrumbs (np. "europe/central_europe/poland")
    
    Returns:
        Path do folderu query
    """
    if not output_dir:
        raise ValueError(f"output_dir cannot be None! source={source}, query={query}")
    
    source_folder = get_source_folder(output_dir, source)
    
    if breadcrumb_path and breadcrumb_path.strip():
        # Use breadcrumb path for hierarchical structure
        # breadcrumb_path already includes the query name at the end
        query_folder = source_folder / breadcrumb_path
    else:
        # Fallback to flat structure
        query_safe = query.lower().replace(" ", "_")
        query_folder = source_folder / query_safe
    
    query_folder.mkdir(parents=True, exist_ok=True)
    return query_folder


def get_output_file_path(
    output_dir: Path,
    source: str,
    country_name: str,
    data_type: str = "countries"
) -> Path:
    """
    Zwraca ścieżkę do pliku JSON dla danego źródła, kraju i typu danych
    
    Args:
        output_dir: Główny katalog wyjściowy
        source: Nazwa źródła
        country_name: Nazwa kraju (lokalizacja)
        data_type: Typ danych - może być dowolny string, np.:
                   - 'countries', 'attractions', 'hotels', 'restaurants'
                   - 'cities', 'regions', 'destinations' (dla Wikivoyage)
                   - 'places', 'guides', etc.
    
    Returns:
        Path do pliku JSON
    """
    source_folder = get_source_folder(output_dir, source)
    country_safe = country_name.lower().replace(" ", "_")
    data_type_safe = data_type.lower().replace(" ", "_")
    filename = f"{country_safe}_{data_type_safe}.json"
    
    return source_folder / filename


def save_data_to_source_file(
    output_dir: Path,
    source: str,
    country_name: str,
    data_type: str,
    data: list,
    append: bool = False
) -> Path:
    """
    Zapisuje dane do pliku JSON w folderze źródła
    
    Args:
        output_dir: Główny katalog wyjściowy
        source: Nazwa źródła
        country_name: Nazwa kraju
        data_type: Typ danych
        data: Lista danych do zapisania
        append: Jeśli True, dołącza do istniejącego pliku
    
    Returns:
        Path do zapisanego pliku
    """
    import json
    
    output_file = get_output_file_path(output_dir, source, country_name, data_type)
    
    if append and output_file.exists():
        # Wczytaj istniejące dane
        with open(output_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        
        # Dodaj nowe dane (unikaj duplikatów)
        existing_ids = {item.get('source_url') for item in existing_data if item.get('source_url')}
        for item in data:
            if item.get('source_url') not in existing_ids:
                existing_data.append(item)
        
        data = existing_data
    
    # Zapisz dane
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    return output_file


def group_by_source(items: List[Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Grupuje elementy według źródła
    
    Args:
        items: Lista elementów z atrybutem 'source' (może być Pydantic model lub dict)
    
    Returns:
        Słownik {source: [items_as_dict]}
    """
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    
    for item in items:
        # Wyciągnij source i konwertuj do dict
        if hasattr(item, 'model_dump'):
            # Pydantic model
            item_dict = item.model_dump(mode='python')
            source = item_dict.get('source', 'unknown')
        elif isinstance(item, dict):
            # Już dict
            item_dict = item
            source = item.get('source', 'unknown')
        else:
            # Spróbuj wyciągnąć source jako atrybut
            source = getattr(item, 'source', 'unknown')
            # Spróbuj konwertować do dict
            if hasattr(item, '__dict__'):
                item_dict = item.__dict__
            else:
                item_dict = {'source': source}
        
        if source not in grouped:
            grouped[source] = []
        
        grouped[source].append(item_dict)
    
    return grouped


def save_html_file(
    output_dir: Path,
    source: str,
    query: str,
    html_content: str,
    breadcrumb_path: Optional[str] = None
) -> Path:
    """
    Zapisuje oryginalny plik HTML w strukturze: source/query/html/query.html
    lub source/breadcrumb_path/html/query.html jeśli breadcrumb_path jest podane
    
    Przykład: wikivoyage/poland/html/poland.html
    lub: wikivoyage/europe/central_europe/poland/html/poland.html
    
    Args:
        output_dir: Główny katalog wyjściowy
        source: Nazwa źródła
        query: Nazwa query (np. 'poland', 'warsaw')
        html_content: Zawartość HTML do zapisania
        breadcrumb_path: Opcjonalna ścieżka breadcrumbs (np. "europe/central_europe/poland")
    
    Returns:
        Path do zapisanego pliku HTML
    """
    query_folder = get_query_folder(output_dir, source, query, breadcrumb_path)
    query_safe = query.lower().replace(" ", "_")
    
    # Create html folder in query folder
    html_folder = query_folder / "html"
    html_folder.mkdir(parents=True, exist_ok=True)
    
    # Save HTML file
    html_file = html_folder / f"{query_safe}.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return html_file


def save_markdown_file(
    output_dir: Path,
    source: str,
    query: str,
    markdown_content: str,
    breadcrumb_path: Optional[str] = None
) -> Path:
    """
    Zapisuje plik Markdown w strukturze: source/query/markdown/query.md
    lub source/breadcrumb_path/markdown/query.md jeśli breadcrumb_path jest podane
    
    Przykład: wikipedia/poland/markdown/poland.md
    lub: wikipedia/europe/central_europe/poland/markdown/poland.md
    
    Args:
        output_dir: Główny katalog wyjściowy
        source: Nazwa źródła
        query: Nazwa query (np. 'poland', 'warsaw')
        markdown_content: Zawartość Markdown do zapisania
        breadcrumb_path: Opcjonalna ścieżka breadcrumbs (np. "europe/central_europe/poland")
    
    Returns:
        Path do zapisanego pliku Markdown
    """
    query_folder = get_query_folder(output_dir, source, query, breadcrumb_path)
    query_safe = query.lower().replace(" ", "_")
    
    # Create markdown folder in query folder
    markdown_folder = query_folder / "markdown"
    markdown_folder.mkdir(parents=True, exist_ok=True)
    
    # Save Markdown file
    markdown_file = markdown_folder / f"{query_safe}.md"
    with open(markdown_file, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    return markdown_file


def save_section_json(
    output_dir: Path,
    source: str,
    query: str,
    section_name: str,
    section_data: Any,
    query_id: str = None,
    parent_query_id: str = None,
    parent_query: str = None,
    node_type: str = None,
    unique_node_id: str = None
) -> Path:
    """
    Zapisuje dane sekcji do pliku JSON w strukturze: source/query/json/section_name.json
    
    Przykład: wikivoyage/poland/json/regions.json
    
    Args:
        output_dir: Główny katalog wyjściowy
        source: Nazwa źródła
        query: Nazwa query (np. 'poland', 'warsaw')
        section_name: Nazwa sekcji (np. 'regions', 'cities', 'understand')
        section_data: Dane sekcji do zapisania (może być dict, list, str, etc.)
        query_id: ID zapytania (hex hash) - opcjonalne
        parent_query_id: ID zapytania rodzica (dla rekurencyjnie pobranych stron) - opcjonalne
        parent_query: Nazwa zapytania rodzica - opcjonalne
        node_type: Typ node'a (np. 'country', 'city', 'region') - opcjonalne
        unique_node_id: Unikalny ID node'a w formacie {source}_{query_id} - opcjonalne
    
    Returns:
        Path do zapisanego pliku JSON
    """
    import json
    
    query_folder = get_query_folder(output_dir, source, query)
    section_safe = section_name.lower().replace(" ", "_")
    
    # Utwórz folder json w folderze query
    json_folder = query_folder / "json"
    json_folder.mkdir(parents=True, exist_ok=True)
    
    # Nazwa pliku to nazwa sekcji
    json_file = json_folder / f"{section_safe}.json"
    
    # Przygotuj dane do zapisu
    if isinstance(section_data, dict):
        # Jeśli to dict, dodaj metadane
        data_to_save = section_data.copy()
        if query_id:
            data_to_save["query_id"] = query_id
        if parent_query_id:
            data_to_save["parent_query_id"] = parent_query_id
        if parent_query:
            data_to_save["parent_query"] = parent_query
        if node_type:
            data_to_save["node_type"] = node_type
        if unique_node_id:
            data_to_save["unique_node_id"] = unique_node_id
    else:
        # Jeśli to string/list, opakuj w dict
        data_to_save = {
            "content": section_data,
            "section_name": section_name,
            "query": query
        }
        if query_id:
            data_to_save["query_id"] = query_id
        if parent_query_id:
            data_to_save["parent_query_id"] = parent_query_id
        if parent_query:
            data_to_save["parent_query"] = parent_query
        if node_type:
            data_to_save["node_type"] = node_type
        if unique_node_id:
            data_to_save["unique_node_id"] = unique_node_id
    
    # Zapisz dane
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data_to_save, f, indent=2, ensure_ascii=False, default=str)
    
    return json_file


def save_main_json(
    output_dir: Path,
    source: str,
    query: str,
    data: Dict[str, Any],
    node_type: Optional[str] = None,
    unique_node_id: Optional[str] = None,
    breadcrumb_path: Optional[str] = None
) -> Path:
    """
    Zapisuje główny plik JSON z wszystkimi danymi w strukturze: source/query/json/query.json
    lub source/breadcrumb_path/json/query.json jeśli breadcrumb_path jest podane
    
    Przykład: wikivoyage/poland/json/poland.json
    lub: wikivoyage/europe/central_europe/poland/json/poland.json
    
    Args:
        output_dir: Główny katalog wyjściowy
        source: Nazwa źródła
        query: Nazwa query (np. 'poland', 'warsaw')
        data: Wszystkie dane do zapisania (dict z wszystkimi sekcjami i metadanymi)
        node_type: Typ node'a (np. 'country', 'city', 'region') - opcjonalne
        unique_node_id: Unikalny ID node'a w formacie {source}_{query_id} - opcjonalne
        breadcrumb_path: Opcjonalna ścieżka breadcrumbs (np. "europe/central_europe/poland")
    
    Returns:
        Path do zapisanego pliku JSON
    """
    import json
    
    query_folder = get_query_folder(output_dir, source, query, breadcrumb_path)
    query_safe = query.lower().replace(" ", "_")
    
    # Utwórz folder json w folderze query
    json_folder = query_folder / "json"
    json_folder.mkdir(parents=True, exist_ok=True)
    
    # Główny plik JSON w folderze json
    json_file = json_folder / f"{query_safe}.json"
    
    # Dodaj metadane Graph RAG jeśli dostępne
    if node_type:
        data["node_type"] = node_type
    if unique_node_id:
        data["unique_node_id"] = unique_node_id
    
    # Zapisz dane
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    return json_file


def save_graph_structure(
    output_dir: Path,
    source: str,
    query: str,
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    breadcrumb_path: Optional[str] = None
) -> Path:
    """
    Zapisuje strukturę grafową do graph.json w strukturze: source/query/graph/graph.json
    lub source/breadcrumb_path/graph/graph.json jeśli breadcrumb_path jest podane
    
    Przykład: wikivoyage/poland/graph/graph.json
    lub: wikivoyage/europe/central_europe/poland/graph/graph.json
    
    Args:
        output_dir: Główny katalog wyjściowy
        source: Nazwa źródła
        query: Nazwa query (np. 'poland', 'warsaw')
        nodes: Lista node'ów z metadanymi
        edges: Lista edge'ów z relacjami
        breadcrumb_path: Opcjonalna ścieżka breadcrumbs (np. "europe/central_europe/poland")
    
    Returns:
        Path do zapisanego pliku graph.json
    """
    import json
    
    query_folder = get_query_folder(output_dir, source, query, breadcrumb_path)
    
    # Utwórz folder graph w folderze query
    graph_folder = query_folder / "graph"
    graph_folder.mkdir(parents=True, exist_ok=True)
    
    # Plik graph.json w folderze graph
    graph_file = graph_folder / "graph.json"
    
    graph_data = {
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "source": source,
            "query": query,
            "node_count": len(nodes),
            "edge_count": len(edges)
        }
    }
    
    # Zapisz dane
    with open(graph_file, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False, default=str)
    
    return graph_file


def update_global_graph(
    output_dir: Path,
    source: str,
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]]
) -> Path:
    """
    Aktualizuje globalny graf dla źródła (append nodes i edges)
    
    Struktura: source/graph.json
    
    Args:
        output_dir: Główny katalog wyjściowy
        source: Nazwa źródła
        nodes: Lista node'ów do dodania
        edges: Lista edge'ów do dodania
    
    Returns:
        Path do zapisanego pliku graph.json
    """
    import json
    
    source_folder = get_source_folder(output_dir, source)
    global_graph_file = source_folder / "graph.json"
    
    # Wczytaj istniejący graf lub utwórz nowy
    if global_graph_file.exists():
        with open(global_graph_file, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
        existing_nodes = {node.get("id"): node for node in graph_data.get("nodes", [])}
        existing_edges = {(edge.get("source"), edge.get("target"), edge.get("type")): edge 
                         for edge in graph_data.get("edges", [])}
    else:
        graph_data = {
            "nodes": [],
            "edges": [],
            "metadata": {
                "source": source,
                "node_count": 0,
                "edge_count": 0
            }
        }
        existing_nodes = {}
        existing_edges = {}
    
    # Dodaj nowe node'y (unikaj duplikatów)
    for node in nodes:
        node_id = node.get("id")
        if node_id and node_id not in existing_nodes:
            graph_data["nodes"].append(node)
            existing_nodes[node_id] = node
    
    # Dodaj nowe edge'y (unikaj duplikatów)
    for edge in edges:
        edge_key = (edge.get("source"), edge.get("target"), edge.get("type"))
        if edge_key not in existing_edges:
            graph_data["edges"].append(edge)
            existing_edges[edge_key] = edge
    
    # Zaktualizuj metadane
    graph_data["metadata"]["node_count"] = len(graph_data["nodes"])
    graph_data["metadata"]["edge_count"] = len(graph_data["edges"])
    
    # Zapisz zaktualizowany graf
    with open(global_graph_file, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False, default=str)
    
    return global_graph_file

