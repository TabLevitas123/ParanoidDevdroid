# config/database.py

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
import os
from typing import Generator

Base = declarative_base()

class DatabaseConfig:
    def __init__(self, db_url: str = None):
        self.database_url = db_url or os.getenv(
            'DATABASE_URL',
            'sqlite+aiosqlite:///./test.db'
        )
        
        # Create sync engine for setup and utilities
        self.sync_engine = create_engine(
            self.database_url.replace('+aiosqlite', ''),
            connect_args={"check_same_thread": False},
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10
        )
        
        # Create async engine for main application
        self.async_engine = create_async_engine(
            self.database_url,
            pool_size=5,
            max_overflow=10
        )
        
        # Create session factories
        self.SessionLocal = sessionmaker(bind=self.sync_engine)
        self.AsyncSessionLocal = sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    def get_db(self) -> Generator:
        """Synchronous database session"""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    async def get_async_db(self) -> AsyncSession:
        """Asynchronous database session"""
        async with self.AsyncSessionLocal() as session:
            yield session

    def create_database(self):
        """Create all tables"""
        Base.metadata.create_all(self.sync_engine)

    def drop_database(self):
        """Drop all tables"""
        Base.metadata.drop_all(self.sync_engine)

# Test database configuration
class TestDatabaseConfig(DatabaseConfig):
    def __init__(self):
        super().__init__('sqlite+aiosqlite:///./test/test.db')
        self.create_database()

    def cleanup(self):
        """Cleanup test database"""
        self.drop_database()

# Create default database configuration
database = DatabaseConfig()

# Create test database configuration
test_database = TestDatabaseConfig()
