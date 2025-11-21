"""
Test data endpoints for populating knowledge base with sample data
Note: This endpoint should use Knowledge Management Service for write operations
This is kept for backward compatibility but should be migrated
"""
from fastapi import APIRouter, Depends, HTTPException, status
import httpx

from app.api.v1.schemas import DocumentUploadResponse
from domain.ports.document_port import IDocumentRepository
from domain.ports.processor_port import IDocumentProcessor
from infrastructure.adapters.document_repository_adapter import DocumentRepository
from infrastructure.adapters.processor_adapter import DocumentProcessor
from infrastructure.database.session import get_db
from config import get_settings

settings = get_settings()

router = APIRouter()


def get_document_repository() -> IDocumentRepository:
    """Dependency injection for document repository"""
    db = next(get_db())
    return DocumentRepository(db)


def get_document_processor() -> IDocumentProcessor:
    """Dependency injection for document processor"""
    return DocumentProcessor()


@router.post("/populate-sample", response_model=dict)
async def populate_sample_data(
    document_repo: IDocumentRepository = Depends(get_document_repository),
    processor: IDocumentProcessor = Depends(get_document_processor)
):
    """Populate knowledge base with sample travel data"""
    
    sample_documents = [
        {
            "filename": "paris_travel_guide.txt",
            "content": """Paris Travel Guide

Paris, the capital of France, is one of the most beautiful cities in the world. 
Known as the City of Light, Paris is famous for its art, culture, and cuisine.

Top Attractions:
- Eiffel Tower: The iconic iron lattice tower, built in 1889. Best visited at sunset.
- Louvre Museum: Home to the Mona Lisa and thousands of other artworks.
- Notre-Dame Cathedral: Gothic masterpiece (currently under restoration).
- Champs-Élysées: Famous avenue leading to the Arc de Triomphe.
- Montmartre: Historic hilltop district with the Sacré-Cœur Basilica.

Best Time to Visit:
Spring (April-June) and Fall (September-October) offer mild weather and fewer crowds.

Local Cuisine:
Try croissants, baguettes, escargot, coq au vin, and of course, French wine.

Transportation:
The Paris Metro is efficient and covers the entire city. Consider a Paris Visite pass for unlimited travel.""",
            "content_type": "text/plain"
        },
        {
            "filename": "tokyo_travel_guide.txt",
            "content": """Tokyo Travel Guide

Tokyo, Japan's bustling capital, is a fascinating blend of traditional and ultra-modern.

Top Attractions:
- Senso-ji Temple: Tokyo's oldest temple in Asakusa district.
- Shibuya Crossing: The world's busiest pedestrian crossing.
- Tokyo Skytree: Tallest tower in Japan with panoramic views.
- Tsukiji Outer Market: Fresh seafood and traditional Japanese food.
- Meiji Shrine: Peaceful Shinto shrine dedicated to Emperor Meiji.

Best Time to Visit:
Spring (March-May) for cherry blossoms, or Fall (September-November) for pleasant weather.

Local Cuisine:
Sushi, ramen, tempura, yakitori, and matcha desserts are must-tries.

Transportation:
The JR Yamanote Line circles central Tokyo. Get a JR Pass for tourists if traveling around Japan.""",
            "content_type": "text/plain"
        },
        {
            "filename": "new_york_travel_guide.txt",
            "content": """New York City Travel Guide

New York City, the Big Apple, is one of the world's most vibrant cities.

Top Attractions:
- Statue of Liberty: Symbol of freedom, accessible by ferry.
- Central Park: 843-acre park in the heart of Manhattan.
- Times Square: The crossroads of the world, especially magical at night.
- Empire State Building: Art Deco skyscraper with observation decks.
- Brooklyn Bridge: Historic bridge connecting Manhattan and Brooklyn.

Best Time to Visit:
Spring (April-June) and Fall (September-November) offer the best weather.

Local Cuisine:
Pizza, bagels, hot dogs, pastrami sandwiches, and New York-style cheesecake.

Transportation:
The subway system is extensive. Consider a MetroCard for unlimited rides.""",
            "content_type": "text/plain"
        }
    ]
    
    processed_count = 0
    total_chunks = 0
    
    # Knowledge Management Service URL for write operations
    km_service_url = getattr(settings, 'knowledge_management_service_url', 'http://localhost:8007')
    
    try:
        async with httpx.AsyncClient() as client:
            for doc_data in sample_documents:
                # Upload document to Knowledge Management Service
                files = {
                    'file': (doc_data["filename"], doc_data["content"].encode('utf-8'), doc_data["content_type"])
                }
                
                try:
                    response = await client.post(
                        f"{km_service_url}/api/v1/documents/upload",
                        files=files,
                        timeout=60.0
                    )
                    
                    if response.status_code == 201:
                        result = response.json()
                        processed_count += 1
                        total_chunks += result.get('chunks_created', 0)
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=f"Failed to upload {doc_data['filename']}: {response.status_code} - {response.text}"
                        )
                except httpx.RequestError as e:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Failed to connect to Knowledge Management Service: {str(e)}"
                    )
        
        return {
            "status": "success",
            "message": f"Successfully populated {processed_count} sample documents",
            "documents_processed": processed_count,
            "total_chunks": total_chunks
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to populate sample data: {str(e)}"
        )

