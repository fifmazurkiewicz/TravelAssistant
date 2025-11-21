"""
Memory reader port (interface) - Read operations only
Note: Write operations are handled by Knowledge Management Service
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class IMemoryReader(ABC):
    """Port dla czytania memory (READ operations)"""
    
    @abstractmethod
    async def get_conversation_history(
        self,
        user_id: int,
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Pobiera historię konwersacji"""
        pass
    
    @abstractmethod
    async def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """Pobiera preferencje użytkownika"""
        pass
    
    @abstractmethod
    async def get_relevant_semantic_memories(
        self,
        user_id: int,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Pobiera relevant semantic memories dla zapytania (vector search)"""
        pass
    
    @abstractmethod
    async def get_all_user_conversations(
        self,
        user_id: int
    ) -> List[Dict[str, Any]]:
        """Pobiera wszystkie conversation memories dla użytkownika"""
        pass

