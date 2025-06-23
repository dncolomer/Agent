#!/usr/bin/env python3
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool

class DatabaseConfig:
    """
    Configures the database connection settings, including connection pooling
    and environment-specific configurations. Ensures scalability and performance optimization.
    """

    def __init__(self):
        self.db_url = self._get_database_url()
        self.engine = self._create_engine()
        self.SessionLocal = self._create_session()

    def _get_database_url(self):
        """
        Retrieves the database URL from environment variables.
        Raises an exception if the URL is not found.
        """
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            raise ValueError("DATABASE_URL environment variable not set")
        return db_url

    def _create_engine(self):
        """
        Creates a SQLAlchemy engine with connection pooling.
        Adjusts pool size and timeout for performance optimization.
        """
        return create_engine(
            self.db_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=1800
        )

    def _create_session(self):
        """
        Creates a scoped session factory for database interactions.
        """
        return scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=self.engine))

    def get_session(self):
        """
        Provides a session for database operations.
        """
        return self.SessionLocal()

# Example usage:
# db_config = DatabaseConfig()
# session = db_config.get_session()
# try:
#     # Perform database operations
# finally:
#     session.close()