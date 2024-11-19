# tests/test_db.py

import sqlite3
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class TestDatabase:
    def __init__(self, db_path: str = "./test/db/test.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
    def setup(self):
        """Setup test database"""
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to database
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # Create tables
        self._create_tables()
        logger.info("Test database setup complete")
        
    def _create_tables(self):
        """Create necessary tables"""
        self.cursor.executescript("""
            -- Users table
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            );

            -- Wallets table
            CREATE TABLE IF NOT EXISTS wallets (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                address TEXT UNIQUE NOT NULL,
                name TEXT,
                balance REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            -- Agents table
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                wallet_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id)
            );
        """)
        self.conn.commit()
    
    def cleanup(self):
        """Cleanup database"""
        if self.conn:
            self.conn.close()
        
        try:
            Path(self.db_path).unlink()
            logger.info("Test database cleaned up")
        except FileNotFoundError:
            pass

def setup_test_db():
    """Setup test database"""
    db = TestDatabase()
    db.setup()
    return db

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Test database setup
    db = setup_test_db()
    print("Database setup successful")
    db.cleanup()
