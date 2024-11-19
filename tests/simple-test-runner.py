# simple_test_runner.py

import logging
from pathlib import Path
import sys
from typing import Dict, Any
import uuid
from datetime import datetime

from tests.test_db import TestDatabase
from tests.test_config import TestData, setup_test_env
from utils.logger import CustomLogger

logger = CustomLogger("test_runner", "test.log")

class SimpleTestRunner:
    """Simple test runner for MVP functionality"""
    
    def __init__(self):
        self.db = None
        self.test_data = TestData()
        self.test_results: Dict[str, Any] = {
            "passed": [],
            "failed": []
        }
    
    def setup(self):
        """Setup test environment"""
        try:
            logger.info("Setting up test environment...")
            
            # Setup environment variables
            setup_test_env()
            
            # Setup test database
            self.db = TestDatabase()
            self.db.setup()
            
            logger.info("Test environment setup complete")
            return True
            
        except Exception as e:
            logger.error(f"Setup failed: {str(e)}")
            return False

    def run_tests(self):
        """Run all tests"""
        try:
            logger.info("Running tests...")
            
            # Test user operations
            self._test_user_operations()
            
            # Test wallet operations
            self._test_wallet_operations()
            
            # Test agent operations
            self._test_agent_operations()
            
            # Print results
            self._print_results()
            
            return len(self.test_results["failed"]) == 0
            
        except Exception as e:
            logger.error(f"Tests failed: {str(e)}")
            return False

    def _test_user_operations(self):
        """Test user management"""
        try:
            logger.info("Testing user operations...")
            
            # Test user creation
            user_data = self.test_data.get_test_user()
            user_id = str(uuid.uuid4())
            
            self.db.cursor.execute("""
                INSERT INTO users (id, username, email, password_hash)
                VALUES (?, ?, ?, ?)
            """, (user_id, user_data["username"], user_data["email"], "test_hash"))
            self.db.conn.commit()
            
            # Test user retrieval
            self.db.cursor.execute(
                "SELECT * FROM users WHERE email = ?",
                (user_data["email"],)
            )
            result = self.db.cursor.fetchone()
            
            assert result is not None
            assert result[1] == user_data["username"]
            
            self.test_results["passed"].append("User operations")
            
        except Exception as e:
            logger.error(f"User operations test failed: {str(e)}")
            self.test_results["failed"].append(("User operations", str(e)))

    def _test_wallet_operations(self):
        """Test wallet management"""
        try:
            logger.info("Testing wallet operations...")
            
            # Get test user
            self.db.cursor.execute("SELECT id FROM users LIMIT 1")
            user_id = self.db.cursor.fetchone()[0]
            
            # Create wallet
            wallet_data = self.test_data.get_test_wallet()
            wallet_id = str(uuid.uuid4())
            address = f"0x{uuid.uuid4().hex}"
            
            self.db.cursor.execute("""
                INSERT INTO wallets (id, user_id, address, name, balance)
                VALUES (?, ?, ?, ?, ?)
            """, (wallet_id, user_id, address, wallet_data["name"], 
                 wallet_data["initial_balance"]))
            self.db.conn.commit()
            
            # Test wallet retrieval
            self.db.cursor.execute(
                "SELECT * FROM wallets WHERE address = ?",
                (address,)
            )
            result = self.db.cursor.fetchone()
            
            assert result is not None
            assert result[3] == wallet_data["name"]
            assert float(result[4]) == wallet_data["initial_balance"]
            
            self.test_results["passed"].append("Wallet operations")
            
        except Exception as e:
            logger.error(f"Wallet operations test failed: {str(e)}")
            self.test_results["failed"].append(("Wallet operations", str(e)))

    def _test_agent_operations(self):
        """Test agent management"""
        try:
            logger.info("Testing agent operations...")
            
            # Get test user
            self.db.cursor.execute("SELECT id FROM users LIMIT 1")
            user_id = self.db.cursor.fetchone()[0]
            
            # Create agent
            agent_data = self.test_data.get_test_agent()
            agent_id = str(uuid.uuid4())
            
            self.db.cursor.execute("""
                INSERT INTO agents (id, owner_id, name, description, status)
                VALUES (?, ?, ?, ?, ?)
            """, (agent_id, user_id, agent_data["name"], 
                 agent_data["description"], "active"))
            self.db.conn.commit()
            
            # Test agent retrieval
            self.db.cursor.execute(
                "SELECT * FROM agents WHERE name = ?",
                (agent_data["name"],)
            )
            result = self.db.cursor.fetchone()
            
            assert result is not None
            assert result[2] == agent_data["name"]
            assert result[3] == agent_data["description"]
            
            self.test_results["passed"].append("Agent operations")
            
        except Exception as e:
            logger.error(f"Agent operations test failed: {str(e)}")
            self.test_results["failed"].append(("Agent operations", str(e)))

    def _print_results(self):
        """Print test results"""
        print("\nTest Results:")
        print("=============")
        
        print("\nPassed Tests:")
        for test in self.test_results["passed"]:
            print(f"✓ {test}")
        
        if self.test_results["failed"]:
            print("\nFailed Tests:")
            for test, error in self.test_results["failed"]:
                print(f"✗ {test}")
                print(f"  Error: {error}")
        
        print(f"\nTotal: {len(self.test_results['passed'])} passed, "
              f"{len(self.test_results['failed'])} failed")

    def cleanup(self):
        """Cleanup test environment"""
        try:
            if self.db:
                self.db.cleanup()
            logger.info("Test cleanup complete")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")

def main():
    """Main test execution"""
    runner = SimpleTestRunner()
    try:
        # Setup
        if not runner.setup():
            logger.error("Test setup failed")
            return 1
        
        # Run tests
        success = runner.run_tests()
        
        if success:
            logger.info("All tests passed!")
            return 0
        else:
            logger.error("Some tests failed!")
            return 1
        
    except Exception as e:
        logger.error(f"Test execution failed: {str(e)}")
        return 1
        
    finally:
        runner.cleanup()

if __name__ == "__main__":
    sys.exit(main())
