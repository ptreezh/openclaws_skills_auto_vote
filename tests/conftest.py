"""
Pytest configuration and fixtures for Skills Arena tests.

This module provides shared fixtures for test database setup and teardown.
"""
import pytest
import os
from scripts.database.db import db


@pytest.fixture(scope="session")
def db_config():
    """Provide database configuration for tests."""
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "skills_arena"),
    }


@pytest.fixture(scope="session")
async def database(db_config):
    """
    Initialize database connection pool for the test session.

    This fixture is called once per test session and handles
    initialization and cleanup of the database connection pool.
    """
    # Configure db module with test settings
    os.environ["DB_HOST"] = db_config["host"]
    os.environ["DB_PORT"] = str(db_config["port"])
    os.environ["DB_USER"] = db_config["user"]
    os.environ["DB_PASSWORD"] = db_config["password"]
    os.environ["DB_NAME"] = db_config["database"]

    try:
        await db.init()
        yield db
    finally:
        await db.close()


# Skip database tests if PostgreSQL is not available
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "requires_db: marks tests as requiring database connection"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (no database required)"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify collected test items to add skip markers for database tests
    when database is not available.
    """
    try:
        import asyncio
        import asyncpg

        async def check_db():
            try:
                conn = await asyncpg.connect(
                    host=os.getenv("DB_HOST", "localhost"),
                    port=int(os.getenv("DB_PORT", 5432)),
                    user=os.getenv("DB_USER", "postgres"),
                    database=os.getenv("DB_NAME", "skills_arena"),
                )
                await conn.close()
                return True
            except Exception:
                return False

        db_available = asyncio.run(check_db())
    except Exception:
        db_available = False

    if not db_available:
        skip_marker = pytest.mark.skip(
            reason="PostgreSQL database not available - set DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, and DB_NAME environment variables"
        )
        for item in items:
            # Skip tests that require database but don't have unit marker
            if "requires_db" in item.keywords or (
                "database" in item.fixturenames
                and "unit" not in item.keywords
                and not item.get_closest_marker("unit")
            ):
                item.add_marker(skip_marker)
