"""
User repository adapter (SQLAlchemy implementation)
"""
from typing import Optional

from sqlalchemy.orm import Session

from domain.entities.user import User, UserPreferences
from domain.ports.user_port import IUserRepository
from infrastructure.database.models import UserModel, UserPreferencesModel


class UserRepository(IUserRepository):
    """SQLAlchemy implementation of user repository"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _to_entity(self, model: UserModel) -> User:
        """Convert database model to domain entity"""
        return User(
            id=model.id,
            username=model.username,
            email=model.email,
            hashed_password=model.hashed_password,
            full_name=model.full_name,
            is_active=model.is_active,
            is_admin=model.is_admin,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
    
    def _to_model(self, entity: User) -> UserModel:
        """Convert domain entity to database model"""
        return UserModel(
            id=entity.id,
            username=entity.username,
            email=entity.email,
            hashed_password=entity.hashed_password,
            full_name=entity.full_name,
            is_active=entity.is_active,
            is_admin=entity.is_admin,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
    
    async def create(self, user: User) -> User:
        """Create new user"""
        db_user = self._to_model(user)
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return self._to_entity(db_user)
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        db_user = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        return self._to_entity(db_user) if db_user else None
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        db_user = self.db.query(UserModel).filter(UserModel.username == username).first()
        return self._to_entity(db_user) if db_user else None
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        db_user = self.db.query(UserModel).filter(UserModel.email == email).first()
        return self._to_entity(db_user) if db_user else None
    
    async def update(self, user: User) -> User:
        """Update user"""
        db_user = self.db.query(UserModel).filter(UserModel.id == user.id).first()
        if db_user:
            db_user.username = user.username
            db_user.email = user.email
            db_user.full_name = user.full_name
            db_user.is_active = user.is_active
            db_user.is_admin = user.is_admin
            db_user.updated_at = user.updated_at
            self.db.commit()
            self.db.refresh(db_user)
            return self._to_entity(db_user)
        raise ValueError(f"User with id {user.id} not found")
    
    async def delete(self, user_id: int) -> bool:
        """Delete user"""
        db_user = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if db_user:
            self.db.delete(db_user)
            self.db.commit()
            return True
        return False
    
    async def get_user_preferences(self, user_id: int) -> Optional[UserPreferences]:
        """Get user preferences"""
        db_prefs = self.db.query(UserPreferencesModel).filter(
            UserPreferencesModel.user_id == user_id
        ).first()
        if db_prefs:
            return UserPreferences(
                user_id=db_prefs.user_id,
                search_context_preference=db_prefs.search_context_preference,
                preferred_language=db_prefs.preferred_language,
                currency=db_prefs.currency,
                created_at=db_prefs.created_at,
                updated_at=db_prefs.updated_at
            )
        return None
    
    async def update_user_preferences(
        self,
        user_id: int,
        search_context_preference: Optional[str] = None,
        preferred_language: Optional[str] = None,
        currency: Optional[str] = None
    ) -> UserPreferences:
        """Update user preferences"""
        db_prefs = self.db.query(UserPreferencesModel).filter(
            UserPreferencesModel.user_id == user_id
        ).first()
        
        if not db_prefs:
            # Create new preferences
            db_prefs = UserPreferencesModel(
                user_id=user_id,
                search_context_preference=search_context_preference or "both",
                preferred_language=preferred_language or "en",
                currency=currency or "USD"
            )
            self.db.add(db_prefs)
        else:
            # Update existing preferences
            if search_context_preference is not None:
                db_prefs.search_context_preference = search_context_preference
            if preferred_language is not None:
                db_prefs.preferred_language = preferred_language
            if currency is not None:
                db_prefs.currency = currency
            from datetime import datetime
            db_prefs.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(db_prefs)
        
        return UserPreferences(
            user_id=db_prefs.user_id,
            search_context_preference=db_prefs.search_context_preference,
            preferred_language=db_prefs.preferred_language,
            currency=db_prefs.currency,
            created_at=db_prefs.created_at,
            updated_at=db_prefs.updated_at
        )

