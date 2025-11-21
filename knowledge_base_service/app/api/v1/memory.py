"""
Memory endpoints - READ operations dla memory

Endpointy do odczytu memory (preferencje użytkownika, conversation history, semantic memories).
Zgodnie z architekturą hybrid - READ operations w knowledge_base_service.

UWAGA: Wymaga utworzenia memory schema w PostgreSQL (zobacz MEMORY_HYBRID_IMPLEMENTATION.md)
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session  # type: ignore

from app.api.v1.schemas import (
    ConversationMemoryResponse,
    ConversationMessageResponse,
    UserPreferencesResponse,
)
from domain.ports.memory_port import IMemoryReader  # type: ignore
from infrastructure.adapters.memory_reader_adapter import MemoryReaderAdapter  # type: ignore
from infrastructure.database.session import get_db

router = APIRouter(prefix="/memory", tags=["memory"])


def get_memory_reader(db: Session = Depends(get_db)) -> IMemoryReader:
    """Dependency injection dla Memory Reader"""
    return MemoryReaderAdapter(db)


@router.get("/preferences/{user_id}", response_model=UserPreferencesResponse)
async def get_user_preferences(
    user_id: int = Path(..., description="ID użytkownika", gt=0),
    memory_reader: IMemoryReader = Depends(get_memory_reader)
):
    """
    Pobiera preferencje użytkownika
    
    Zwraca:
    - preferences: słownik z preferencjami (travel_style, budget, etc.)
    - favorite_destinations: lista ulubionych miejsc
    - travel_history: historia podróży
    """
    try:
        preferences_data = await memory_reader.get_user_preferences(user_id=user_id)
        
        # preferences_data może zawierać updated_at jeśli jest w odpowiedzi z bazy
        return UserPreferencesResponse(
            user_id=user_id,
            preferences=preferences_data.get("preferences", {}),
            favorite_destinations=preferences_data.get("favorite_destinations", []),
            travel_history=preferences_data.get("travel_history", []),
            updated_at=preferences_data.get("updated_at")  # Jeśli jest w odpowiedzi
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user preferences: {str(e)}"
        )


@router.get(
    "/conversation/{user_id}/{session_id}",
    response_model=ConversationMemoryResponse
)
async def get_conversation_memory(
    user_id: int = Path(..., description="ID użytkownika", gt=0),
    session_id: str = Path(..., description="ID sesji konwersacji"),
    limit: Optional[int] = None,
    memory_reader: IMemoryReader = Depends(get_memory_reader)
):
    """
    Pobiera całą conversation memory dla wybranego user_id i session_id
    
    Zwraca:
    - user_id: ID użytkownika
    - session_id: ID sesji
    - messages: lista wszystkich wiadomości w konwersacji
    - total_messages: całkowita liczba wiadomości
    
    Parametry:
    - limit: maksymalna liczba wiadomości do zwrócenia (domyślnie wszystkie)
    """
    try:
        # Pobierz historię konwersacji (bez limitu jeśli limit=None)
        # Użyj dużego limitu aby pobrać wszystkie wiadomości
        messages = await memory_reader.get_conversation_history(
            user_id=user_id,
            session_id=session_id,
            limit=limit if limit is not None else 10000  # Duży limit = wszystkie wiadomości
        )
        
        return ConversationMemoryResponse(
            user_id=user_id,
            session_id=session_id,
            messages=[
                ConversationMessageResponse(
                    role=msg["role"],
                    content=msg["content"],
                    timestamp=msg.get("timestamp")
                )
                for msg in messages
            ],
            total_messages=len(messages)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve conversation memory: {str(e)}"
        )


@router.get(
    "/conversation/{user_id}",
    response_model=List[ConversationMemoryResponse]
)
async def get_all_user_conversations(
    user_id: int = Path(..., description="ID użytkownika", gt=0),
    memory_reader: IMemoryReader = Depends(get_memory_reader)
):
    """
    Pobiera wszystkie conversation memories dla danego użytkownika
    
    Zwraca listę wszystkich sesji konwersacji użytkownika.
    Każda sesja zawiera pełną historię wiadomości.
    
    """
    try:
        # Pobierz wszystkie sesje dla użytkownika
        conversations = await memory_reader.get_all_user_conversations(user_id=user_id)
        
        return [
            ConversationMemoryResponse(
                user_id=conv["user_id"],
                session_id=conv["session_id"],
                messages=[
                    ConversationMessageResponse(
                        role=msg["role"],
                        content=msg["content"],
                        timestamp=msg.get("timestamp")
                    )
                    for msg in conv.get("messages", [])
                ],
                total_messages=len(conv.get("messages", [])),
                created_at=conv.get("created_at"),
                updated_at=conv.get("updated_at")
            )
            for conv in conversations
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user conversations: {str(e)}"
        )

