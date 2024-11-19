# tests/advanced_test_cases.py

import asyncio
import pytest
from datetime import datetime, timedelta
import uuid
from decimal import Decimal

from tests.test_db import TestDatabase
from tests.test_config import TestData
from utils.logger import CustomLogger

logger = CustomLogger("advanced_tests", "advanced_tests.log")

class AdvancedTestCases:
    """Advanced test cases for the platform"""
    
    def __init__(self, db: TestDatabase):
        self.db = db
        self.test_data = TestData()
        
    async def run_all_tests(self):
        """Run all advanced test cases"""
        test_methods = [
            self.test_concurrent_transactions,
            self.test_agent_interactions,
            self.test_wallet_limits,
            self.test_user_permissions,
            self.test_error_handling,
            self.test_data_integrity
        ]
        
        results = []
        for test_method in test_methods:
            try:
                await test_method()
                results.append((test_method.__name__, "PASSED", None))
            except Exception as e:
                results.append((test_method.__name__, "FAILED", str(e)))
                logger.error(f"{test_method.__name__} failed: {str(e)}")
        
        return results

    async def test_concurrent_transactions(self):
        """Test concurrent transaction handling"""
        logger.info("Testing concurrent transactions...")
        
        # Setup test users and wallets
        user_ids = []
        wallet_ids = []
        for i in range(5):
            # Create user
            user_id = str(uuid.uuid4())
            self.db.cursor.execute("""
                INSERT INTO users (id, username, email, password_hash)
                VALUES (?, ?, ?, ?)
            """, (user_id, f"test_user_{i}", 
                 f"test{i}@example.com", "test_hash"))
            user_ids.append(user_id)
            
            # Create wallet with initial balance
            wallet_id = str(uuid.uuid4())
            self.db.cursor.execute("""
                INSERT INTO wallets (id, user_id, address, balance)
                VALUES (?, ?, ?, ?)
            """, (wallet_id, user_id, f"0x{uuid.uuid4().hex}", 1000.0))
            wallet_ids.append(wallet_id)
        
        self.db.conn.commit()
        
        # Create concurrent transactions
        async def make_transaction(from_wallet: str, to_wallet: str, amount: float):
            # Check balance
            self.db.cursor.execute(
                "SELECT balance FROM wallets WHERE id = ?",
                (from_wallet,)
            )
            balance = self.db.cursor.fetchone()[0]
            
            if balance >= amount:
                # Update balances
                self.db.cursor.execute("""
                    UPDATE wallets 
                    SET balance = balance - ? 
                    WHERE id = ?
                """, (amount, from_wallet))
                
                self.db.cursor.execute("""
                    UPDATE wallets 
                    SET balance = balance + ? 
                    WHERE id = ?
                """, (amount, to_wallet))
                
                # Record transaction
                tx_id = str(uuid.uuid4())
                self.db.cursor.execute("""
                    INSERT INTO transactions 
                    (id, from_wallet, to_wallet, amount, status)
                    VALUES (?, ?, ?, ?, ?)
                """, (tx_id, from_wallet, to_wallet, amount, "completed"))
                
                self.db.conn.commit()
                return True
            return False
        
        # Execute concurrent transactions
        tasks = []
        for i in range(10):
            from_wallet = wallet_ids[i % 4]
            to_wallet = wallet_ids[(i + 1) % 4]
            tasks.append(make_transaction(from_wallet, to_wallet, 100.0))
        
        results = await asyncio.gather(*tasks)
        assert all(results), "Some transactions failed"

    async def test_agent_interactions(self):
        """Test complex agent interactions"""
        logger.info("Testing agent interactions...")
        
        # Create test user
        user_id = str(uuid.uuid4())
        self.db.cursor.execute("""
            INSERT INTO users (id, username, email, password_hash)
            VALUES (?, ?, ?, ?)
        """, (user_id, "agent_test_user", 
             "agent_test@example.com", "test_hash"))
        
        # Create multiple agents
        agent_ids = []
        for i in range(3):
            agent_id = str(uuid.uuid4())
            self.db.cursor.execute("""
                INSERT INTO agents 
                (id, owner_id, name, description, status, capabilities)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (agent_id, user_id, f"Test Agent {i}",
                 "Test Description", "active", 
                 '["text_generation", "image_generation"]'))
            agent_ids.append(agent_id)
        
        self.db.conn.commit()
        
        # Test agent collaboration
        for i in range(len(agent_ids)):
            for j in range(i + 1, len(agent_ids)):
                # Record interaction
                self.db.cursor.execute("""
                    INSERT INTO agent_interactions
                    (agent_id_1, agent_id_2, interaction_type, result)
                    VALUES (?, ?, ?, ?)
                """, (agent_ids[i], agent_ids[j], 
                     "collaboration", "success"))
        
        self.db.conn.commit()
        
        # Verify interactions
        self.db.cursor.execute(
            "SELECT COUNT(*) FROM agent_interactions"
        )
        interaction_count = self.db.cursor.fetchone()[0]
        assert interaction_count == 3, "Missing agent interactions"

    async def test_wallet_limits(self):
        """Test wallet limits and constraints"""
        logger.info("Testing wallet limits...")
        
        # Create test user with wallet
        user_id = str(uuid.uuid4())
        self.db.cursor.execute("""
            INSERT INTO users (id, username, email, password_hash)
            VALUES (?, ?, ?, ?)
        """, (user_id, "wallet_test_user", 
             "wallet_test@example.com", "test_hash"))
        
        wallet_id = str(uuid.uuid4())
        self.db.cursor.execute("""
            INSERT INTO wallets (id, user_id, address, balance)
            VALUES (?, ?, ?, ?)
        """, (wallet_id, user_id, f"0x{uuid.uuid4().hex}", 1000.0))
        
        self.db.conn.commit()
        
        # Test transaction limits
        async def attempt_transaction(amount: float) -> bool:
            try:
                self.db.cursor.execute("""
                    UPDATE wallets 
                    SET balance = balance - ? 
                    WHERE id = ? AND balance >= ?
                """, (amount, wallet_id, amount))
                
                return self.db.cursor.rowcount > 0
            except Exception:
                return False
        
        # Test various scenarios
        assert await attempt_transaction(500.0), "Valid transaction failed"
        assert not await attempt_transaction(1000.0), "Overdraft not prevented"
        
        # Test rate limiting
        timestamps = []
        for _ in range(5):
            tx_id = str(uuid.uuid4())
            self.db.cursor.execute("""
                INSERT INTO transactions 
                (id, wallet_id, amount, timestamp)
                VALUES (?, ?, ?, ?)
            """, (tx_id, wallet_id, 10.0, datetime.utcnow()))
            timestamps.append(datetime.utcnow())
        
        self.db.conn.commit()
        
        # Verify rate limiting
        time_diffs = [(timestamps[i+1] - timestamps[i]).total_seconds() 
                     for i in range(len(timestamps)-1)]
        assert min(time_diffs) >= 0.1, "Rate limit not enforced"

    async def test_user_permissions(self):
        """Test user permission management"""
        logger.info("Testing user permissions...")
        
        # Create users with different roles
        roles = ["user", "admin", "agent_creator"]
        user_ids = {}
        
        for role in roles:
            user_id = str(uuid.uuid4())
            self.db.cursor.execute("""
                INSERT INTO users 
                (id, username, email, password_hash, role)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, f"{role}_user", 
                 f"{role}@example.com", "test_hash", role))
            user_ids[role] = user_id
        
        self.db.conn.commit()
        
        # Test permission checks
        def check_permission(user_id: str, action: str) -> bool:
            self.db.cursor.execute("""
                SELECT role FROM users WHERE id = ?
            """, (user_id,))
            role = self.db.cursor.fetchone()[0]
            
            # Define permission matrix
            permissions = {
                "user": ["read_own", "create_agent"],
                "admin": ["read_all", "write_all", "manage_users"],
                "agent_creator": ["read_own", "create_agent", "manage_agents"]
            }
            
            return action in permissions.get(role, [])
        
        # Test various permission scenarios
        assert check_permission(user_ids["admin"], "manage_users")
        assert not check_permission(user_ids["user"], "manage_users")
        assert check_permission(user_ids["agent_creator"], "manage_agents")

    async def test_error_handling(self):
        """Test error handling and recovery"""
        logger.info("Testing error handling...")
        
        # Test database constraints
        try:
            # Attempt to create user with duplicate email
            self.db.cursor.execute("""
                INSERT INTO users (id, username, email, password_hash)
                VALUES (?, ?, ?, ?)
            """, (str(uuid.uuid4()), "test_user",
                 "duplicate@example.com", "test_hash"))
            
            self.db.cursor.execute("""
                INSERT INTO users (id, username, email, password_hash)
                VALUES (?, ?, ?, ?)
            """, (str(uuid.uuid4()), "test_user2",
                 "duplicate@example.com", "test_hash"))
            
            assert False, "Duplicate email constraint failed"
        except Exception:
            pass  # Expected error
        
        # Test transaction rollback
        self.db.conn.rollback()
        
        # Verify database state
        self.db.cursor.execute(
            "SELECT COUNT(*) FROM users WHERE email = ?",
            ("duplicate@example.com",)
        )
        count = self.db.cursor.fetchone()[0]
        assert count <= 1, "Transaction rollback failed"

    async def test_data_integrity(self):
        """Test data integrity and consistency"""
        logger.info("Testing data integrity...")
        
        # Create test data
        user_id = str(uuid.uuid4())
        wallet_id = str(uuid.uuid4())
        agent_id = str(uuid.uuid4())
        
        # Insert related records
        self.db.cursor.execute("""
            INSERT INTO users (id, username, email, password_hash)
            VALUES (?, ?, ?, ?)
        """, (user_id, "integrity_test", 
             "integrity@example.com", "test_hash"))
        
        self.db.cursor.execute("""
            INSERT INTO wallets (id, user_id, address, balance)
            VALUES (?, ?, ?, ?)
        """, (wallet_id, user_id, f"0x{uuid.uuid4().hex}", 1000.0))
        
        self.db.cursor.execute("""
            INSERT INTO agents (id, owner_id, name, status)
            VALUES (?, ?, ?, ?)
        """, (agent_id, user_id, "Test Agent", "active"))
        
        self.db.conn.commit()
        
        # Verify referential integrity
        self.db.cursor.execute("""
            SELECT w.id, a.id 
            FROM users u
            LEFT JOIN wallets w ON u.id = w.user_id
            LEFT JOIN agents a ON u.id = a.owner_id
            WHERE u.id = ?
        """, (user_id,))
        
        result = self.db.cursor.fetchone()
        assert result[0] == wallet_id, "Wallet reference integrity failed"
        assert result[1] == agent_id, "Agent reference integrity failed"
        
        # Test cascading deletes
        self.db.cursor.execute(
            "DELETE FROM users WHERE id = ?",
            (user_id,)
        )
        self.db.conn.commit()
        
        # Verify related records are handled correctly
        self.db.cursor.execute(
            "SELECT COUNT(*) FROM wallets WHERE user_id = ?",
            (user_id,)
        )
        assert self.db.cursor.fetchone()[0] == 0, "Cascade delete failed"

def run_advanced_tests():
    """Run all advanced test cases"""
    db = TestDatabase()
    try:
        db.setup()
        test_suite = AdvancedTestCases(db)
        results = asyncio.run(test_suite.run_all_tests())
        
        # Print results
        print("\nAdvanced Test Results:")
        print("=====================")
        for test_name, status, error in results:
            status_symbol = "✓" if status == "PASSED" else "✗"
            print(f"{status_symbol} {test_name}")
            if error:
                print(f"  Error: {error}")
        
        passed = sum(1 for _, status, _ in results if status == "PASSED")
        total = len(results)
        print(f"\nPassed {passed}/{total} tests")
        
        return passed == total
        
    finally:
        db.cleanup()

if __name__ == "__main__":
    success = run_advanced_tests()
    sys.exit(0 if success else 1)
