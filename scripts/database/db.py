"""
Database connection manager for Skills Arena.
"""
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import asyncpg


# Database configuration from environment variables
# Support both DB_* and POSTGRES_* prefixes for flexibility
DB_CONFIG = {
    "host": os.getenv("DB_HOST") or os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT") or os.getenv("POSTGRES_PORT", "5432")),
    "user": os.getenv("DB_USER") or os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD", "postgres"),
    "database": os.getenv("DB_NAME") or os.getenv("POSTGRES_DB", "skills_arena"),
}


class Database:
    """Database connection manager with connection pooling."""

    def __init__(self):
        """Initialize the database manager."""
        self.pool = None

    async def init(self):
        """Initialize the connection pool."""
        self.pool = await asyncpg.create_pool(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
            min_size=2,
            max_size=10,
        )

    async def close(self):
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Get a connection from the pool.

        Yields:
            asyncpg.Connection: A database connection from the pool.
        """
        async with self.pool.acquire() as connection:
            yield connection


# Global database instance
db = Database()
