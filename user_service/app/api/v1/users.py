"""
User management endpoints
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.v1.auth import get_current_user, get_password_hash
from app.api.v1.schemas import UserPreferencesResponse, UserPreferencesUpdate, UserResponse
from domain.entities.user import User
from domain.ports.user_port import IUserRepository
from infrastructure.adapters.user_repository_adapter import UserRepository
from infrastructure.database.session import get_db

router = APIRouter()


def get_user_repository() -> IUserRepository:
    """Dependency injection for user repository"""
    db = next(get_db())
    return UserRepository(db)


class PasswordUpdateRequest(BaseModel):
    """Password update request schema"""
    hashed_password: str


@router.get("/me/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(
    current_user: User = Depends(get_current_user),
    user_repo: IUserRepository = Depends(get_user_repository)
):
    """Get user preferences"""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID is missing"
        )
    preferences = await user_repo.get_user_preferences(current_user.id)
    return UserPreferencesResponse(
        user_id=current_user.id,
        search_context_preference=preferences.search_context_preference if preferences else "both",
        preferred_language=preferences.preferred_language if preferences else "en",
        currency=preferences.currency if preferences else "USD"
    )


@router.put("/me/preferences", response_model=UserPreferencesResponse)
async def update_user_preferences(
    preferences_update: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    user_repo: IUserRepository = Depends(get_user_repository)
):
    """Update user preferences"""
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID is missing"
        )
    preferences = await user_repo.update_user_preferences(
        current_user.id,
        search_context_preference=preferences_update.search_context_preference,
        preferred_language=preferences_update.preferred_language,
        currency=preferences_update.currency
    )
    return UserPreferencesResponse(
        user_id=preferences.user_id,
        search_context_preference=preferences.search_context_preference,
        preferred_language=preferences.preferred_language,
        currency=preferences.currency
    )


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    user_repo: IUserRepository = Depends(get_user_repository)
):
    """List all users (admin only)"""
    # TODO: Add admin role check
    from infrastructure.database.models import UserModel
    from infrastructure.database.session import get_db
    db = next(get_db())
    users = db.query(UserModel).offset(skip).limit(limit).all()
    return [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at
        )
        for user in users
    ]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    user_repo: IUserRepository = Depends(get_user_repository)
):
    """Get user by ID"""
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at
    )


@router.put("/admin/users/{user_id}/password", response_model=dict)
async def update_user_password_admin(
    user_id: int,
    password_update: PasswordUpdateRequest,
    user_repo: IUserRepository = Depends(get_user_repository)
):
    """Update user password (admin only)"""
    # TODO: Add admin role check
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Update password
    user.hashed_password = password_update.hashed_password
    from datetime import datetime
    user.updated_at = datetime.utcnow()
    updated_user = await user_repo.update(user)
    
    return {"message": "Password updated successfully", "user_id": user_id}

