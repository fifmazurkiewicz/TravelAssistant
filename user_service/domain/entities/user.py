"""
User entity (DDD Aggregate Root)
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """User aggregate root"""
    id: Optional[int] = None
    username: str = ""
    email: str = ""
    hashed_password: str = ""
    full_name: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    def activate(self):
        """Activate user"""
        self.is_active = True
        self.updated_at = datetime.utcnow()
    
    def deactivate(self):
        """Deactivate user"""
        self.is_active = False
        self.updated_at = datetime.utcnow()
    
    def update_profile(self, full_name: Optional[str] = None):
        """Update user profile"""
        if full_name is not None:
            self.full_name = full_name
        self.updated_at = datetime.utcnow()


@dataclass
class UserPreferences:
    """User preferences value object"""
    user_id: int
    search_context_preference: str = "both"  # "personal", "general", "both"
    preferred_language: str = "en"
    currency: str = "USD"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    def update_preferences(
        self,
        search_context_preference: Optional[str] = None,
        preferred_language: Optional[str] = None,
        currency: Optional[str] = None
    ):
        """Update preferences"""
        if search_context_preference is not None:
            self.search_context_preference = search_context_preference
        if preferred_language is not None:
            self.preferred_language = preferred_language
        if currency is not None:
            self.currency = currency
        self.updated_at = datetime.utcnow()

