"""
API request/response schemas
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    """User creation schema"""
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    """User response schema"""
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime


class Token(BaseModel):
    """Token response schema"""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Token data schema"""
    username: Optional[str] = None


class UserPreferencesUpdate(BaseModel):
    """User preferences update schema"""
    search_context_preference: Optional[Literal["personal", "general", "both"]] = None
    preferred_language: Optional[str] = None
    currency: Optional[str] = None


class UserPreferencesResponse(BaseModel):
    """User preferences response schema"""
    user_id: int
    search_context_preference: Literal["personal", "general", "both"]
    preferred_language: str
    currency: str

