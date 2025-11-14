"""
User repository port (interface)
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from domain.entities.user import User, UserPreferences


class IUserRepository(ABC):
    """User repository interface"""
    
    @abstractmethod
    async def create(self, user: User) -> User:
        """Create new user"""
        pass
    
    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        pass
    
    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        pass
    
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        pass
    
    @abstractmethod
    async def update(self, user: User) -> User:
        """Update user"""
        pass
    
    @abstractmethod
    async def delete(self, user_id: int) -> bool:
        """Delete user"""
        pass
    
    @abstractmethod
    async def get_user_preferences(self, user_id: int) -> Optional[UserPreferences]:
        """Get user preferences"""
        pass
    
    @abstractmethod
    async def update_user_preferences(
        self,
        user_id: int,
        search_context_preference: Optional[str] = None,
        preferred_language: Optional[str] = None,
        currency: Optional[str] = None
    ) -> UserPreferences:
        """Update user preferences"""
        pass

