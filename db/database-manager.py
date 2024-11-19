import sqlite3
import logging
from typing import Optional, List, Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Class for managing database connections and operations."""
    def __init__(self, db_path: str):
        if not db_path:
            raise ValueError("Database path must be provided.")
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None

    def connect(self):
        """Establish a connection to the database."""
        try:
            self.connection = sqlite3.connect(self.db_path)
            logger.info("Database connection established.")
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def execute_query(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results."""
        if not self.connection:
            raise RuntimeError("Database connection is not established.")
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or [])
            self.connection.commit()
            columns = [col[0] for col in cursor.description] if cursor.description else []
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            logger.info("Query executed successfully.")
            return results
        except sqlite3.Error as e:
            logger.error(f"Failed to execute query: {e}")
            raise

    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed.")

if __name__ == '__main__':
    manager = DatabaseManager(db_path="test.db")
    manager.connect()
    manager.execute_query("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)")
    manager.execute_query("INSERT INTO test (name) VALUES (?)", ["Sample Name"])
    results = manager.execute_query("SELECT * FROM test")
    print(results)
    manager.close()
