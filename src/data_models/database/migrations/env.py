"""
Alembic migration environment configuration.
"""
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from typing import Any

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import our models and configuration after path setup
try:
    from src.data_models.database.config import db_config
    from src.data_models.database.models import Base
except ImportError as e:
    print(f"Warning: Could not import database modules: {e}")
    print("This may be expected if running without full environment setup")
    # Create a minimal fallback

    class MockBase:
        metadata = None
    Base = MockBase()

    class MockConfig:
        def get_postgres_url(self):
            return os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost/db')
    db_config = MockConfig()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
# Only available when running under Alembic
try:
    config: Any = context.config  # type: ignore
except AttributeError:
    # Running outside of Alembic context (e.g., during testing)
    config = None

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config and hasattr(config, 'config_file_name') and config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_url():
    """Get database URL from configuration."""
    try:
        return db_config.get_postgres_url()
    except Exception as e:
        print(f"Warning: Could not get database URL from config: {e}")
        # Fallback to environment variable
        return os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost/db')


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    try:
        url = get_url()
        context.configure(  # type: ignore
            url=url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )

        with context.begin_transaction():  # type: ignore
            context.run_migrations()  # type: ignore
    except Exception as e:
        print(f"Error running offline migrations: {e}")
        raise


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    if not config:
        print("Warning: No Alembic config available, skipping online migrations")
        return

    try:
        # Override the sqlalchemy.url in the alembic config
        config.set_main_option("sqlalchemy.url", get_url())

        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            context.configure(  # type: ignore
                connection=connection, target_metadata=target_metadata
            )

            with context.begin_transaction():  # type: ignore
                context.run_migrations()  # type: ignore
    except Exception as e:
        print(f"Error running online migrations: {e}")
        raise


def run_migrations():
    """Run migrations based on the current context."""
    try:
        if context.is_offline_mode():  # type: ignore
            run_migrations_offline()
        else:
            run_migrations_online()
    except (AttributeError, NameError):
        # Not running under Alembic context
        print("Warning: Not running under Alembic context, migrations skipped")


# Only run migrations if this file is being executed by Alembic
# Check if we're in an Alembic context by looking for the proxy setup
try:
    # This will fail if not running under Alembic
    _ = context.is_offline_mode  # type: ignore
    # If we get here, we're in Alembic context
    run_migrations()
except (AttributeError, NameError):
    # Not running under Alembic, which is fine for imports/testing
    pass
