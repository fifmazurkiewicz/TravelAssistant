"""
Database session management
"""
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={"options": f"-csearch_path={settings.database_schema},public"} if hasattr(settings, 'database_schema') else {}
)

# Set default schema for all connections
if hasattr(settings, 'database_schema') and settings.database_schema:
    @event.listens_for(engine, "connect")
    def set_search_path(dbapi_conn, connection_record):
        """Set PostgreSQL search_path for each connection"""
        cursor = dbapi_conn.cursor()
        cursor.execute(f"SET search_path TO {settings.database_schema}, public")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

