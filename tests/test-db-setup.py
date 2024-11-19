# tests/setup_test_db.py

import sqlite3
from pathlib import Path

def setup_test_database():
    """Setup SQLite test database with required tables"""
    
    # Ensure test/db directory exists
    db_dir = Path("test/db")
    db_dir.mkdir(parents=True, exist_ok=True)
    
    # Connect to test database
    conn = sqlite3.connect("test/db/test.db")
    cursor = conn.cursor()
    
    # Create tables
    cursor.executescript("""
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

        -- Transactions table
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            from_wallet TEXT,
            to_wallet TEXT,
            amount REAL NOT NULL,
            transaction_type TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            error TEXT,
            metadata TEXT,
            FOREIGN KEY (from_wallet) REFERENCES wallets(id),
            FOREIGN KEY (to_wallet) REFERENCES wallets(id)
        );
    """)
    
    conn.commit()
    conn.close()
    
    print("Test database setup complete")

if __name__ == "__main__":
    setup_test_database()
