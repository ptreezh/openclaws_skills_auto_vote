import asyncio
import asyncpg
import os

async def test_connection():
    try:
        conn = await asyncpg.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            user=os.getenv('DB_USER', 'postgres'),
            database=os.getenv('DB_NAME', 'skills_arena')
        )
        print('Connected to PostgreSQL successfully')
        version = await conn.fetchval('SELECT version()')
        print(f'PostgreSQL version: {version.split(",")[0]}')
        await conn.close()
        return True
    except Exception as e:
        print(f'Failed to connect to PostgreSQL: {e}')
        return False

if __name__ == '__main__':
    result = asyncio.run(test_connection())
    exit(0 if result else 1)
