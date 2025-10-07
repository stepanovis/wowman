"""
Database configuration module.
Handles database connection and session management.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from contextlib import contextmanager

# Load environment variables
load_dotenv()

# Database configuration from environment variables
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'ovulo_dev')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

# Construct database URL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create engine
# Use NullPool for better connection handling in async environments
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False,  # Set to True for SQL query logging during development
    future=True,  # Use SQLAlchemy 2.0 style
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,  # Use SQLAlchemy 2.0 style
)

# Base class for declarative models
Base = declarative_base()


def get_db():
    """
    Dependency for getting database session.
    Usage in FastAPI or other frameworks:

    def some_endpoint(db: Session = Depends(get_db)):
        # use db session here
        pass
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """
    Context manager for database sessions.
    Usage:

    with get_db_session() as session:
        # use session here
        pass
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """
    Initialize database tables.
    This is mainly for testing purposes.
    In production, use Alembic migrations.
    """
    # Import all models to register them with Base
    from models import User, Cycle, NotificationSettings, NotificationLog  # noqa

    Base.metadata.create_all(bind=engine)


def drop_db():
    """
    Drop all database tables.
    WARNING: This will delete all data!
    Use only for testing or development.
    """
    Base.metadata.drop_all(bind=engine)