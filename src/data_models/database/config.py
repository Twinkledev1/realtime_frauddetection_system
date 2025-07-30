"""
Database configuration and connection management.
"""
import os
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
import redis
from redis.exceptions import ConnectionError as RedisConnectionError

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration manager."""

    def __init__(self):
        """Initialize database configuration."""
        self.postgres_config = self._get_postgres_config()
        self.redis_config = self._get_redis_config()

        # Initialize engines and sessions
        self.postgres_engine: Optional[Engine] = None
        self.redis_client: Optional[redis.Redis] = None
        self.SessionLocal: Optional[sessionmaker] = None

        # Initialize connections
        self._initialize_postgres()
        self._initialize_redis()

    def _get_postgres_config(self) -> Dict[str, Any]:
        """Get PostgreSQL configuration from environment variables."""
        return {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'fraud_db'),
            'username': os.getenv('POSTGRES_USER', 'user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'password'),
            'pool_size': int(os.getenv('POSTGRES_POOL_SIZE', '10')),
            'max_overflow': int(os.getenv('POSTGRES_MAX_OVERFLOW', '20')),
            'pool_timeout': int(os.getenv('POSTGRES_POOL_TIMEOUT', '30')),
            'pool_recycle': int(os.getenv('POSTGRES_POOL_RECYCLE', '3600')),
        }

    def _get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration from environment variables."""
        return {
            'host': os.getenv('REDIS_HOST', 'localhost'),
            'port': int(os.getenv('REDIS_PORT', '6379')),
            'db': int(os.getenv('REDIS_DB', '0')),
            'password': os.getenv('REDIS_PASSWORD'),
            'decode_responses': True,
            'socket_timeout': int(os.getenv('REDIS_SOCKET_TIMEOUT', '5')),
            'socket_connect_timeout': int(os.getenv('REDIS_CONNECT_TIMEOUT', '5')),
            'retry_on_timeout': True,
            'health_check_interval': int(os.getenv('REDIS_HEALTH_CHECK_INTERVAL', '30')),
        }

    def _initialize_postgres(self):
        """Initialize PostgreSQL engine and session factory."""
        try:
            # Build connection string
            connection_string = (
                f"postgresql://{self.postgres_config['username']}:{self.postgres_config['password']}"
                f"@{self.postgres_config['host']}:{self.postgres_config['port']}"
                f"/{self.postgres_config['database']}"
            )

            # Create engine with connection pooling
            self.postgres_engine = create_engine(
                connection_string,
                poolclass=QueuePool,
                pool_size=self.postgres_config['pool_size'],
                max_overflow=self.postgres_config['max_overflow'],
                pool_timeout=self.postgres_config['pool_timeout'],
                pool_recycle=self.postgres_config['pool_recycle'],
                echo=os.getenv('SQL_ECHO', 'false').lower() == 'true',
                pool_pre_ping=True,
            )

            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.postgres_engine
            )

            logger.info("PostgreSQL engine initialized successfully")

        except (ImportError, AttributeError, ValueError, RuntimeError, SQLAlchemyError) as e:
            logger.warning(
                "PostgreSQL engine initialization failed (this is expected if PostgreSQL is not running): %s", e)
            logger.info("Creating mock PostgreSQL engine for development")
            self.postgres_engine = None
            self.SessionLocal = None

    def _initialize_redis(self):
        """Initialize Redis client."""
        try:
            self.redis_client = redis.Redis(**self.redis_config)

            # Test connection
            self.redis_client.ping()
            logger.info("Redis client initialized successfully")

        except (ImportError, AttributeError, ValueError, RuntimeError, RedisConnectionError) as e:
            logger.warning(
                "Redis client initialization failed (this is expected if Redis is not running): %s", e)
            logger.info("Creating mock Redis client for development")
            self.redis_client = None

    def get_postgres_url(self) -> str:
        """Get PostgreSQL connection URL."""
        return (
            f"postgresql://{self.postgres_config['username']}:{self.postgres_config['password']}"
            f"@{self.postgres_config['host']}:{self.postgres_config['port']}"
            f"/{self.postgres_config['database']}"
        )

    def get_redis_url(self) -> str:
        """Get Redis connection URL."""
        password_part = f":{self.redis_config['password']}@" if self.redis_config['password'] else ""
        return f"redis://{password_part}{self.redis_config['host']}:{self.redis_config['port']}/{self.redis_config['db']}"

    @contextmanager
    def get_db_session(self) -> Session:
        """Get database session with automatic cleanup."""
        if not self.SessionLocal:
            logger.warning(
                "Database session factory not initialized - skipping database operation")
            yield None
            return

        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error("Database session error: %s", e)
            raise
        finally:
            session.close()

    def get_redis_client(self) -> redis.Redis:
        """Get Redis client instance."""
        if not self.redis_client:
            raise RuntimeError("Redis client not initialized")
        return self.redis_client

    def test_connections(self) -> Dict[str, bool]:
        """Test database connections."""
        results = {}

        # Test PostgreSQL
        try:
            with self.get_db_session() as session:
                if session is not None:
                    from sqlalchemy import text
                    session.execute(text("SELECT 1"))
                    results['postgresql'] = True
                    logger.info("PostgreSQL connection test: SUCCESS")
                else:
                    results['postgresql'] = False
                    logger.warning(
                        "PostgreSQL connection test: SKIPPED - no session available")
        except (AttributeError, ValueError, RuntimeError, SQLAlchemyError) as e:
            results['postgresql'] = False
            logger.error("PostgreSQL connection test: FAILED - %s", e)

        # Test Redis
        try:
            self.redis_client.ping()
            results['redis'] = True
            logger.info("Redis connection test: SUCCESS")
        except (AttributeError, ValueError, RuntimeError, RedisConnectionError) as e:
            results['redis'] = False
            logger.error("Redis connection test: FAILED - %s", e)

        return results

    def close_connections(self):
        """Close all database connections."""
        try:
            if self.postgres_engine:
                self.postgres_engine.dispose()
                logger.info("PostgreSQL connections closed")

            if self.redis_client:
                self.redis_client.close()
                logger.info("Redis connections closed")

        except (AttributeError, ValueError, RuntimeError) as e:
            logger.error("Error closing database connections: %s", e)


# Global database configuration instance
db_config = DatabaseConfig()


def get_db_session() -> Session:
    """Get database session."""
    return db_config.get_db_session()


def get_redis_client() -> redis.Redis:
    """Get Redis client."""
    return db_config.get_redis_client()


def test_database_connections() -> Dict[str, bool]:
    """Test all database connections."""
    return db_config.test_connections()
