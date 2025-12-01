from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
from backend.config import settings

# Create engine using settings
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})


def create_db_and_tables():
    """Create all database tables"""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Dependency for getting database session"""
    with Session(engine) as session:
        yield session

