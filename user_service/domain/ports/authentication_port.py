"""
Authentication service port (interface)
"""
from abc import ABC, abstractmethod
from typing import Optional
from domain.entities.user import User


class IAuthenticationService(ABC):
    """Authentication service interface"""
    
    @abstractmethod
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password"""
        pass
    
    @abstractmethod
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        pass
    
    @abstractmethod
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        pass
    
    @abstractmethod
    async def create_user(
        self,
        username: str,
        email: str,
        hashed_password: str,
        full_name: Optional[str] = None
    ) -> User:
        """Create new user"""
        pass

