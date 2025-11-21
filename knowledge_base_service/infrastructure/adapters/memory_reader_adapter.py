"""
Memory Reader Adapter - READ operations dla memory
"""
from typing import Any, Dict, List, Optional

from sqlalchemy import text  # type: ignore
from sqlalchemy.orm import Session  # type: ignore

from config import get_settings
from domain.ports.memory_port import IMemoryReader
from infrastructure.adapters.embedding_adapter import EmbeddingService
from infrastructure.adapters.vector_store.vector_store_factory import VectorStoreFactory

settings = get_settings()


class MemoryReaderAdapter(IMemoryReader):
    """Adapter do czytania memory z shared storage"""
    
    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService()
        # Memory schema i collection name z konfiguracji
        self.memory_schema = getattr(settings, 'memory_database_schema', 'memory')
        self.memory_collection = getattr(settings, 'memory_vector_collection', 'user_memories')
        # Stwórz vector store dla memory collection
        self.vector_store = VectorStoreFactory.create(collection_name=self.memory_collection)
    
    async def get_conversation_history(
        self,
        user_id: int,
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Pobiera historię konwersacji z PostgreSQL"""
        if session_id:
            query = text(f"""
                SELECT messages
                FROM {self.memory_schema}.conversation_memory
                WHERE user_id = :user_id
                AND session_id = :session_id
                ORDER BY updated_at DESC
                LIMIT 1
            """)
            params = {"user_id": user_id, "session_id": session_id}
        else:
            query = text(f"""
                SELECT messages
                FROM {self.memory_schema}.conversation_memory
                WHERE user_id = :user_id
                ORDER BY updated_at DESC
                LIMIT 1
            """)
            params = {"user_id": user_id}
        
        result = self.db.execute(query, params).fetchone()
        
        if result and result[0]:
            # messages to JSONB - wyciągnij ostatnie N wiadomości
            messages = result[0]
            return [
                {
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg.get("timestamp")  # Zachowaj timestamp jeśli jest
                }
                for msg in messages[-limit:]
            ]
        
        return []
    
    async def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """Pobiera preferencje użytkownika z PostgreSQL"""
        query = text(f"""
            SELECT preferences, favorite_destinations, travel_history, updated_at
            FROM {self.memory_schema}.user_preferences
            WHERE user_id = :user_id
        """)
        
        result = self.db.execute(query, {"user_id": user_id}).fetchone()
        
        if result:
            return {
                "preferences": result[0] or {},
                "favorite_destinations": result[1] or [],
                "travel_history": result[2] or [],
                "updated_at": result[3]  # updated_at z bazy
            }
        
        return {
            "preferences": {},
            "favorite_destinations": [],
            "travel_history": [],
            "updated_at": None
        }
    
    async def get_relevant_semantic_memories(
        self,
        user_id: int,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Pobiera relevant semantic memories przez vector search"""
        # 1. Stwórz embedding zapytania
        query_embedding = await self.embedding_service.embed_text(query)
        
        # 2. Wyszukaj w vector store z filtrem user_id
        results = await self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            filters={"user_id": user_id},
            query_text=query,  # Dla hybrid search (BM25)
            use_hybrid=True
        )
        
        # 3. Zwróć jako listę dict
        # results już jest List[Dict[str, Any]] z kluczami: content, metadata, score
        return results
    
    async def get_all_user_conversations(
        self,
        user_id: int
    ) -> List[Dict[str, Any]]:
        """Pobiera wszystkie conversation memories dla użytkownika"""
        query = text(f"""
            SELECT 
                user_id,
                session_id,
                messages,
                created_at,
                updated_at
            FROM {self.memory_schema}.conversation_memory
            WHERE user_id = :user_id
            ORDER BY updated_at DESC
        """)
        
        results = self.db.execute(query, {"user_id": user_id}).fetchall()
        
        conversations = []
        for row in results:
            # row[2] to messages (JSONB)
            messages_list = row[2] or []
            conversations.append({
                "user_id": row[0],
                "session_id": row[1],
                "messages": [
                    {
                        "role": msg["role"],
                        "content": msg["content"],
                        "timestamp": msg.get("timestamp")
                    }
                    for msg in messages_list
                ],
                "created_at": row[3],
                "updated_at": row[4]
            })
        
        return conversations

