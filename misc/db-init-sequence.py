# db_init_sequence.py

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event
from typing import Optional

from models.core_models import Base
from utils.logger import CustomLogger

logger = CustomLogger("db_init", "database.log")

class DatabaseManager:
    """Manages database connections and initialization"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.async_session_factory = None
        
    async def initialize(self) -> bool:
        """Initialize database connection and tables"""
        try:
            # Create async engine
            self.engine = create_async_engine(
                self.database_url,
                echo=True,  # Set to False in production
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True
            )
            
            # Create async session factory
            self.async_session_factory = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create tables
            async with self.engine.begin() as conn:
                # Drop all tables in test environment
                if "test" in self.database_url:
                    await conn.run_sync(Base.metadata.drop_all)
                # Create all tables
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("Database initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise
    
    async def get_session(self) -> AsyncSession:
        """Get database session"""
        if not self.async_session_factory:
            raise RuntimeError("Database not initialized")
        
        async with self.async_session_factory() as session:
            try:
                yield session
            finally:
                await session.close()
    
    async def cleanup(self):
        """Cleanup database connections"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")

# Test database initialization
async def test_db_connection(database_url: str):
    """Test database connection and basic operations"""
    db = DatabaseManager(database_url)
    try:
        # Initialize database
        await db.initialize()
        
        # Test session creation
        async for session in db.get_session():
            # Test query
            result = await session.execute("SELECT 1")
            assert result is not None
            logger.info("Database connection test successful")
            
        return True
        
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        raise
    finally:
        await db.cleanup()

if __name__ == "__main__":
    # Test with SQLite
    database_url = "sqlite+aiosqlite:///./test.db"
    asyncio.run(test_db_connection(database_url))
