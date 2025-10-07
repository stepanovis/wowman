"""
Session management module for database operations.
Provides utilities for managing database sessions safely.
"""

from utils.logger import get_logger, log_database_operation
from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from database.config import SessionLocal, engine

# Set up logging
logger = get_logger(__name__)


class DatabaseSession:
    """
    Database session manager with automatic rollback on errors.
    """

    def __init__(self):
        """Initialize the database session manager."""
        self.session_factory = SessionLocal

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.

        Automatically commits on success and rollbacks on error.

        Yields:
            Session: SQLAlchemy database session

        Example:
            with db_session.get_session() as session:
                user = session.query(User).first()
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
            logger.debug("Database session committed successfully")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error occurred, rolling back: {str(e)}")
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error occurred, rolling back: {str(e)}")
            raise
        finally:
            session.close()
            logger.debug("Database session closed")

    def get_session_no_commit(self) -> Session:
        """
        Get a database session without automatic commit.

        Useful for read-only operations or when manual commit control is needed.

        Returns:
            Session: SQLAlchemy database session

        Note:
            Remember to close the session manually when done.
        """
        return self.session_factory()

    @contextmanager
    def transaction(self, session: Optional[Session] = None) -> Generator[Session, None, None]:
        """
        Create a transaction within an existing session or new one.

        Args:
            session: Existing session to use, or None to create new one

        Yields:
            Session: SQLAlchemy database session

        Example:
            with db_session.transaction() as tx:
                user = tx.query(User).first()
                user.username = "new_name"
        """
        if session:
            # Use existing session, don't close it
            yield session
        else:
            # Create new session with automatic cleanup
            with self.get_session() as new_session:
                yield new_session


# Global session manager instance
db_session = DatabaseSession()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database session (FastAPI compatible).

    Yields:
        Session: SQLAlchemy database session

    Example:
        def some_endpoint(db: Session = Depends(get_db)):
            users = db.query(User).all()
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def atomic_operation() -> Generator[Session, None, None]:
    """
    Context manager for atomic database operations.

    Ensures that all operations within the context are executed
    as a single transaction.

    Yields:
        Session: SQLAlchemy database session

    Example:
        with atomic_operation() as session:
            user = create_user(session, telegram_id=123)
            cycle = create_cycle(session, user_id=user.id)
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
        logger.debug("Atomic operation committed successfully")
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Atomic operation failed, rolling back: {str(e)}")
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error in atomic operation, rolling back: {str(e)}")
        raise
    finally:
        session.close()


def test_connection() -> bool:
    """
    Test database connection.

    Returns:
        bool: True if connection successful, False otherwise
    """
    from sqlalchemy import text

    try:
        with db_session.get_session() as session:
            # Execute a simple query to test connection
            session.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
            return True
    except SQLAlchemyError as e:
        logger.error(f"Database connection test failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during connection test: {str(e)}")
        return False