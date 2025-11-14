"""
SQLAlchemy database models
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class UserModel(Base):
    """User database model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True)
    
    preferences = relationship("UserPreferencesModel", back_populates="user", uselist=False)


class UserPreferencesModel(Base):
    """User preferences database model"""
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    search_context_preference = Column(String(20), default="both", nullable=False)
    preferred_language = Column(String(10), default="en", nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True)
    
    user = relationship("UserModel", back_populates="preferences")

