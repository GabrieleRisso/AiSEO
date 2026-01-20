import os
from sqlmodel import SQLModel, Session, create_engine
from pathlib import Path

# Support both SQLite (local dev) and PostgreSQL (production)
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Render uses postgres:// but SQLAlchemy needs postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    # PostgreSQL doesn't need check_same_thread
    engine = create_engine(DATABASE_URL)
else:
    # Fallback to SQLite for local development
    DATABASE_PATH = Path(__file__).parent / "aiseo.db"
    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def create_db_and_tables():
    """Create all tables in the database"""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency for FastAPI routes"""
    with Session(engine) as session:
        yield session
