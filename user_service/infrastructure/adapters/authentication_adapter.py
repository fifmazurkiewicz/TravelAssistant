"""
Authentication service adapter
"""
from typing import Optional

import bcrypt

from domain.entities.user import User
from domain.ports.authentication_port import IAuthenticationService
from domain.ports.user_port import IUserRepository


def truncate_password_for_bcrypt(password: str) -> str:
    """Truncate password to 72 bytes for bcrypt compatibility"""
    if isinstance(password, bytes):
        password = password.decode('utf-8', errors='ignore')
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password = password_bytes[:72].decode('utf-8', errors='ignore')
    return password


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password using bcrypt directly (to avoid passlib initialization issues)"""
    try:
        # Truncate password to 72 bytes for bcrypt compatibility
        truncated_password = truncate_password_for_bcrypt(plain_password)
        # Use bcrypt directly - hashed_password is already a bcrypt hash string
        return bcrypt.checkpw(truncated_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


class AuthenticationService(IAuthenticationService):
    """Authentication service implementation"""
    
    def __init__(self, user_repository: IUserRepository, pwd_context=None):
        # pwd_context is kept for compatibility but we use bcrypt directly
        self.user_repository = user_repository
        self.pwd_context = pwd_context
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password"""
        user = await self.user_repository.get_by_username(username)
        if not user:
            return None
        # Use bcrypt directly to avoid passlib initialization issues
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return await self.user_repository.get_by_username(username)
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return await self.user_repository.get_by_email(email)
    
    async def create_user(
        self,
        username: str,
        email: str,
        hashed_password: str,
        full_name: Optional[str] = None
    ) -> User:
        """Create new user"""
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            full_name=full_name
        )
        return await self.user_repository.create(user)

