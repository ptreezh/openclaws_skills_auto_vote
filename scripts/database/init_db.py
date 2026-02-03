#!/usr/bin/env python3
"""
Skills Arena - PostgreSQL Database Initialization Script

This script initializes the PostgreSQL database with the schema for social features.
It uses asyncpg for async PostgreSQL connections.

Usage:
    python init_db.py

Environment Variables:
    POSTGRES_HOST     - PostgreSQL host (default: localhost)
    POSTGRES_PORT     - PostgreSQL port (default: 5432)
    POSTGRES_DB       - Database name (default: skills_arena)
    POSTGRES_USER     - Database user (default: postgres)
    POSTGRES_PASSWORD - Database password (required, no default)
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import asyncpg


# Database configuration from environment variables with defaults
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'skills_arena'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', '')
}


class DatabaseInitializer:
    """Handles PostgreSQL database initialization"""

    def __init__(self, config: dict):
        """
        Initialize the database initializer

        Args:
            config: Database connection configuration
        """
        self.config = config
        self.schema_path = Path(__file__).parent / 'schema.sql'

    def validate_config(self) -> bool:
        """
        Validate database configuration

        Returns:
            True if configuration is valid, False otherwise
        """
        if not self.config['password']:
            print("❌ Error: POSTGRES_PASSWORD environment variable is required")
            print("\nPlease set the environment variable:")
            print("  export POSTGRES_PASSWORD='your_password'")
            print("\nOr run with:")
            print("  POSTGRES_PASSWORD='your_password' python init_db.py")
            return False

        if not self.schema_path.exists():
            print(f"❌ Error: Schema file not found: {self.schema_path}")
            return False

        return True

    def read_schema(self) -> str:
        """
        Read the SQL schema file

        Returns:
            Schema SQL as string
        """
        with open(self.schema_path, 'r', encoding='utf-8') as f:
            return f.read()

    async def test_connection(self) -> bool:
        """
        Test database connection

        Returns:
            True if connection successful, False otherwise
        """
        try:
            print(f"🔌 Testing connection to PostgreSQL...")
            print(f"   Host: {self.config['host']}")
            print(f"   Port: {self.config['port']}")
            print(f"   Database: {self.config['database']}")
            print(f"   User: {self.config['user']}")

            conn = await asyncpg.connect(**self.config)
            version = await conn.fetchval('SELECT version()')
            await conn.close()

            print(f"✅ Connected successfully!")
            print(f"   {version.split(',')[0]}")
            return True

        except asyncpg.PostgresError as e:
            print(f"❌ Connection failed: {e}")
            print("\nPlease check:")
            print("  1. PostgreSQL is running")
            print("  2. Connection parameters are correct")
            print("  3. Database exists (or create it first)")
            print("  4. User has necessary privileges")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False

    async def initialize_schema(self) -> bool:
        """
        Initialize database schema

        Returns:
            True if successful, False otherwise
        """
        try:
            # Read schema SQL
            print(f"\n📄 Reading schema from: {self.schema_path}")
            schema_sql = self.read_schema()

            # Connect to database
            print("🔌 Connecting to database...")
            conn = await asyncpg.connect(**self.config)

            # Execute schema
            print("🚀 Executing schema...")
            await conn.execute(schema_sql)

            # Close connection
            await conn.close()

            print("✅ Schema initialized successfully!")
            return True

        except asyncpg.PostgresError as e:
            print(f"❌ Database error: {e}")
            return False
        except Exception as e:
            print(f"❌ Error initializing schema: {e}")
            return False

    async def verify_tables(self) -> bool:
        """
        Verify that all tables were created successfully

        Returns:
            True if all tables exist, False otherwise
        """
        expected_tables = {
            'agents', 'skills', 'agent_skills',
            'comments', 'votes', 'downloads',
            'following', 'communities'
        }

        try:
            conn = await asyncpg.connect(**self.config)

            # Get all table names
            query = """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
            """
            rows = await conn.fetch(query)
            actual_tables = {row['tablename'] for row in rows}

            await conn.close()

            # Check for missing tables
            missing_tables = expected_tables - actual_tables
            if missing_tables:
                print(f"⚠️  Warning: Missing tables: {missing_tables}")
                return False

            print(f"\n✅ Verified {len(actual_tables)} tables:")
            for table in sorted(actual_tables):
                print(f"   ✓ {table}")

            return True

        except Exception as e:
            print(f"❌ Error verifying tables: {e}")
            return False

    async def run(self) -> int:
        """
        Run the complete initialization process

        Returns:
            Exit code (0 for success, 1 for failure)
        """
        print("=" * 60)
        print("Skills Arena - Database Initialization")
        print("=" * 60)

        # Validate configuration
        if not self.validate_config():
            return 1

        # Test connection
        if not await self.test_connection():
            return 1

        # Initialize schema
        if not await self.initialize_schema():
            return 1

        # Verify tables
        if not await self.verify_tables():
            return 1

        print("\n" + "=" * 60)
        print("🎉 Database initialization completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Run your API server to start using the database")
        print("  2. Test the API endpoints")
        print("  3. Create sample data if needed")

        return 0


async def main():
    """Main entry point"""
    initializer = DatabaseInitializer(DB_CONFIG)
    exit_code = await initializer.run()
    sys.exit(exit_code)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Initialization cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
