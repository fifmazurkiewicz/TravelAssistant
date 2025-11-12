"""
Data ingestion API endpoints
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from app.api.v1.schemas import IngestionRequest, IngestionResponse
from config import get_settings
from exceptions import ExternalServiceError, ValidationError

# Import from data_ingestion_service using relative import
# We're in app/api/v1/, so we need to go up 3 levels to reach data_ingestion_service root
import sys
from pathlib import Path

# Add data_ingestion_service to path if not already there
current_file = Path(__file__).resolve()
service_root = current_file.parent.parent.parent.parent  # data_ingestion_service
if str(service_root) not in sys.path:
    sys.path.insert(0, str(service_root))

from run_ingestion import DataIngestionOrchestrator

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


@router.post("/ingest", response_model=IngestionResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_data(
    request: IngestionRequest
):
    """
    Ingest data from external sources for a country
    
    This endpoint fetches data from multiple sources (Wikipedia, Wikidata, TripAdvisor, etc.)
    and saves it to JSON files. Optionally, it can add the data to the knowledge base.
    """
    try:
        # Validate request
        if not request.country_name or not request.country_name.strip():
            raise ValidationError("country_name is required")
        
        # Initialize orchestrator with LLM support if enabled
        orchestrator = DataIngestionOrchestrator(
            enabled_sources=request.enabled_sources,
            output_dir=settings.output_dir,
            wikivoyage_language=settings.wikivoyage_language,
            wikivoyage_max_depth=settings.wikivoyage_max_depth,
            wikivoyage_level_1_sections=settings.wikivoyage_level_1_sections_list,
            wikivoyage_level_2_sections=settings.wikivoyage_level_2_sections_list,
            use_llm=request.use_llm_analysis,
            llm_api_key=settings.openrouter_api_key,
            llm_base_url=settings.openrouter_base_url,
            llm_model=settings.llm_model
        )
        
        # Fetch data
        results = await orchestrator.fetch_country_data(request.country_name)
        
        # Save results
        orchestrator.save_results(results, request.country_name)
        
        # Prepare output files list (now grouped by source)
        # Import from utils - data_ingestion_service is already in sys.path
        from utils.file_manager import get_output_file_path, group_by_source, get_query_folder
        from pathlib import Path
        
        output_files = []
        
        # Add files from standard sources (wikipedia, wikidata)
        for data_type, items in results.items():
            if items:
                # Grupuj według źródła i dodaj ścieżki do plików
                grouped_by_source = group_by_source(items)
                for source, source_items in grouped_by_source.items():
                    # Skip Wikivoyage - it uses new folder structure
                    if source.startswith("wikivoyage"):
                        continue
                    output_file = get_output_file_path(
                        orchestrator.output_dir,
                        source,
                        request.country_name,
                        data_type
                    )
                    if output_file.exists():
                        output_files.append(str(output_file))
        
        # Add Wikivoyage files from new folder structure
        wikivoyage_sources = ["wikivoyage", "wikivoyage_en", "wikivoyage_pl"]
        for source in wikivoyage_sources:
            # Try to find query folder (may be in hierarchical structure)
            query_folder = get_query_folder(
                orchestrator.output_dir,
                source,
                request.country_name,
                breadcrumb_path=None  # Will search in flat structure first
            )
            
            # Check if folder exists
            if query_folder.exists():
                # Add main JSON file
                json_file = query_folder / "json" / f"{request.country_name.lower().replace(' ', '_')}.json"
                if json_file.exists():
                    output_files.append(str(json_file))
                
                # Add HTML file
                html_file = query_folder / "html" / f"{request.country_name.lower().replace(' ', '_')}.html"
                if html_file.exists():
                    output_files.append(str(html_file))
                
                # Add graph file
                graph_file = query_folder / "graph" / "graph.json"
                if graph_file.exists():
                    output_files.append(str(graph_file))
            
            # Also check hierarchical structure (e.g., europe/central_europe/poland)
            # Search for query folder recursively
            wikivoyage_base = orchestrator.output_dir / "wikivoyage"
            if wikivoyage_base.exists():
                for query_folder_path in wikivoyage_base.rglob(request.country_name.lower().replace(" ", "_")):
                    if query_folder_path.is_dir():
                        # Check if this is the query folder (has json/html/graph subfolders)
                        if (query_folder_path / "json").exists():
                            json_file = query_folder_path / "json" / f"{request.country_name.lower().replace(' ', '_')}.json"
                            if json_file.exists() and str(json_file) not in output_files:
                                output_files.append(str(json_file))
                            
                            html_file = query_folder_path / "html" / f"{request.country_name.lower().replace(' ', '_')}.html"
                            if html_file.exists() and str(html_file) not in output_files:
                                output_files.append(str(html_file))
                            
                            graph_file = query_folder_path / "graph" / "graph.json"
                            if graph_file.exists() and str(graph_file) not in output_files:
                                output_files.append(str(graph_file))
                        break  # Found the main query folder, no need to search further
        
        # Optionally add to knowledge base
        added_to_kb = False
        if request.add_to_knowledge_base:
            try:
                import httpx as http_client
                
                # Convert ingested data to text documents and upload to knowledge base
                kb_url = settings.knowledge_base_service_url
                documents_added = 0
                
                # Create text documents from ingested data
                for data_type, items in results.items():
                    if not items:
                        continue
                    
                    # Convert each item to a text document
                    for item in items:
                        try:
                            # Create a text representation of the data
                            if hasattr(item, 'model_dump'):
                                item_dict = item.model_dump()
                            elif isinstance(item, dict):
                                item_dict = item
                            else:
                                continue
                            
                            # Create document content from item
                            content_parts = []
                            if data_type == "countries" and isinstance(item_dict, dict):
                                content_parts.append(f"Country: {item_dict.get('name', request.country_name)}")
                                if 'description' in item_dict:
                                    content_parts.append(item_dict['description'])
                                if 'capital' in item_dict:
                                    content_parts.append(f"Capital: {item_dict['capital']}")
                            elif data_type == "attractions" and isinstance(item_dict, dict):
                                content_parts.append(f"Attraction: {item_dict.get('name', 'Unknown')}")
                                if 'description' in item_dict:
                                    content_parts.append(item_dict['description'])
                                if 'location' in item_dict:
                                    content_parts.append(f"Location: {item_dict['location']}")
                            
                            if not content_parts:
                                continue
                            
                            document_content = "\n\n".join(content_parts)
                            
                            # Upload to knowledge base service
                            filename = f"{request.country_name}_{data_type}_{item_dict.get('name', 'item')}.txt"
                            filename = filename.replace(" ", "_").replace("/", "_")[:100]  # Sanitize filename
                            
                            async with http_client.AsyncClient() as client:
                                files = {
                                    'file': (filename, document_content.encode('utf-8'), 'text/plain')
                                }
                                response = await client.post(
                                    f"{kb_url}/api/v1/documents/upload",
                                    files=files,
                                    timeout=60.0
                                )
                                if response.status_code == 201:
                                    documents_added += 1
                                else:
                                    logger.warning(f"Failed to upload {filename}: {response.status_code} - {response.text}")
                        
                        except Exception as e:
                            logger.warning(f"Error adding item to knowledge base: {e}")
                            continue
                
                added_to_kb = documents_added > 0
                if added_to_kb:
                    logger.info(f"Added {documents_added} documents to knowledge base")
                else:
                    logger.warning("No documents were added to knowledge base")
                    
            except Exception as e:
                logger.error(f"Error adding data to knowledge base: {e}", exc_info=True)
                # Don't fail the whole request if KB addition fails
                added_to_kb = False
        
        # Prepare response
        results_summary = {
            "countries": len(results.get("countries", [])),
            "attractions": len(results.get("attractions", [])),
            "hotels": len(results.get("hotels", [])),
            "restaurants": len(results.get("restaurants", []))
        }
        
        return IngestionResponse(
            status="success",
            country_name=request.country_name,
            enabled_sources=orchestrator.enabled_sources,
            results=results_summary,
            output_files=output_files,
            added_to_kb=added_to_kb,
            message=f"Successfully ingested data for {request.country_name}"
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ExternalServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Error ingesting data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest data: {str(e)}"
        )


@router.get("/sources")
async def list_sources():
    """List available data sources"""
    return {
        "sources": [
            {
                "name": "wikipedia",
                "description": "Wikipedia articles via MediaWiki API",
                "supports": ["countries", "attractions"]
            },
            {
                "name": "wikidata",
                "description": "Structured data via SPARQL queries",
                "supports": ["countries", "attractions"]
            },
            {
                "name": "wikivoyage",
                "description": "Wikivoyage travel guides (English) via MediaWiki API - practical travel information",
                "supports": ["countries", "attractions"]
            },
            {
                "name": "tripadvisor",
                "description": "TripAdvisor reviews and ratings (web scraping)",
                "supports": ["attractions", "hotels", "restaurants"]
            },
            {
                "name": "lonely_planet",
                "description": "Lonely Planet travel guides (web scraping)",
                "supports": ["countries", "attractions"]
            },
            {
                "name": "world_travel_guide",
                "description": "World Travel Guide (web scraping)",
                "supports": ["countries", "attractions"]
            },
            {
                "name": "travel_independent",
                "description": "Travel Independent (web scraping)",
                "supports": ["countries", "attractions"]
            }
        ]
    }

