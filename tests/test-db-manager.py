# test_db_manager.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import asyncio
import logging
from config.database_models import Base

logger = logging.getLogger(__name__)

class TestDatabaseManager:
    """Simplified database manager for testing"""
    def __init__(self, database_url: str = "sqlite:///./test.db"):
        self.database_url = database_url
        self.engine = create_engine(
            self.database_url,
            echo=True,
            connect_args={"check_same_thread": False}  # Needed for SQLite
        )
        self.SessionLocal = sessionmaker(bind=self.engine)

    async def initialize(self):
        """Initialize database"""
        try:
            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    async def cleanup(self):
        """Cleanup database"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("Database cleaned up")
        except Exception as e:
            logger.error(f"Database cleanup failed: {e}")
            raise

    async def get_session(self):
        """Get database session"""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()

# Initialize test database
async def init_test_db():
    db = TestDatabaseManager()
    await db.initialize()
    return db

if __name__ == "__main__":
    # Quick test
    asyncio.run(init_test_db())
    print("Test database initialized")
