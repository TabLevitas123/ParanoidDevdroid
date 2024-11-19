# init_db.py

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from config.database_models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_db(database_url: str):
    """Initialize database with required tables"""
    try:
        # Create async engine
        engine = create_async_engine(
            database_url,
            echo=True
        )
        
        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.drop_all)  # Clean slate for testing
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database initialized successfully")
        return engine
        
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

if __name__ == "__main__":
    database_url = "sqlite+aiosqlite:///./test.db"  # Using SQLite for testing
    asyncio.run(init_db(database_url))
