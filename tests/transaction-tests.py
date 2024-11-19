# tests/transaction_tests.py

import asyncio
import pytest
from datetime import datetime
import uuid
from decimal import Decimal
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor

from tests.test_db import TestDatabase
from tests.test_config import TestData
from utils.logger import CustomLogger

logger = CustomLogger("transaction_tests", "transaction_tests.log")

class TransactionTests:
    """Comprehensive transaction testing suite"""
    
    def __init__(self):
        self.db = TestDatabase()
        self.test_data = TestData()
        self.test_users: List[Dict[str, Any]] = []
        self.test_wallets: List[Dict[str, Any]] = []
        self.test_agents: List[Dict[str, Any]] = []
        self.transactions: List[Dict[str, Any]] = []
        
    async def setup(self):
        """Setup test environment with sample data"""
        self.db.setup()
        
        # Create test tables for transactions if not exists
        self.db.cursor.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                from_wallet TEXT,
                to_wallet TEXT,
                amount DECIMAL(36,18),
                transaction_type TEXT,
                status TEXT,
                created_at TIMESTAMP,
                completed_at TIMESTAMP,
                error TEXT,
                metadata JSON,
                FOREIGN KEY (from_wallet) REFERENCES wallets(id),
                FOREIGN KEY (to_wallet) REFERENCES wallets(id)
            );
            
            CREATE TABLE IF NOT EXISTS transaction_locks (
                wallet_id TEXT PRIMARY KEY,
                locked_at TIMESTAMP,
                locked_by TEXT
            );
            
            CREATE TABLE IF NOT EXISTS transaction_events (
                id TEXT PRIMARY KEY,
                transaction_id TEXT,
                event_type TEXT,
                event_data JSON,
                created_at TIMESTAMP,
                FOREIGN KEY (transaction_id) REFERENCES transactions(id)
            );
        """)
        
        # Create test users and wallets
        await self._create_test_users(5)  # Create 5 test users
        await self._create_test_wallets()  # Create wallets for users
        await self._create_test_agents()   # Create some test agents
        
        logger.info("Test environment setup complete")

    async def _create_test_users(self, count: int):
        """Create test users"""
        for i in range(count):
            user_id = str(uuid.uuid4())
            user_data = {
                "id": user_id,
                "username": f"test_user_{i}",
                "email": f"test{i}@example.com",
                "password_hash": "test_hash"
            }
            
            self.db.cursor.execute("""
                INSERT INTO users (id, username, email, password_hash)
                VALUES (?, ?, ?, ?)
            """, (user_data["id"], user_data["username"],
                 user_data["email"], user_data["password_hash"]))
            
            self.test_users.append(user_data)
        
        self.db.conn.commit()

    async def _create_test_wallets(self):
        """Create test wallets for users"""
        for user in self.test_users:
            wallet_id = str(uuid.uuid4())
            wallet_data = {
                "id": wallet_id,
                "user_id": user["id"],
                "address": f"0x{uuid.uuid4().hex}",
                "balance": Decimal("1000.0")  # Initial balance
            }
            
            self.db.cursor.execute("""
                INSERT INTO wallets (id, user_id, address, balance)
                VALUES (?, ?, ?, ?)
            """, (wallet_data["id"], wallet_data["user_id"],
                 wallet_data["address"], wallet_data["balance"]))
            
            self.test_wallets.append(wallet_data)
        
        self.db.conn.commit()

    async def _create_test_agents(self):
        """Create test agents"""
        for user in self.test_users[:2]:  # Create agents for first 2 users
            agent_id = str(uuid.uuid4())
            agent_data = {
                "id": agent_id,
                "owner_id": user["id"],
                "name": f"Test Agent {len(self.test_agents)}",
                "status": "active"
            }
            
            self.db.cursor.execute("""
                INSERT INTO agents (id, owner_id, name, status)
                VALUES (?, ?, ?, ?)
            """, (agent_data["id"], agent_data["owner_id"],
                 agent_data["name"], agent_data["status"]))
            
            self.test_agents.append(agent_data)
        
        self.db.conn.commit()

    async def acquire_lock(self, wallet_id: str, lock_id: str) -> bool:
        """Attempt to acquire a transaction lock"""
        try:
            self.db.cursor.execute("""
                INSERT INTO transaction_locks (wallet_id, locked_at, locked_by)
                VALUES (?, ?, ?)
            """, (wallet_id, datetime.utcnow(), lock_id))
            
            self.db.conn.commit()
            return True
        except Exception:
            return False

    async def release_lock(self, wallet_id: str, lock_id: str) -> bool:
        """Release a transaction lock"""
        try:
            self.db.cursor.execute("""
                DELETE FROM transaction_locks
                WHERE wallet_id = ? AND locked_by = ?
            """, (wallet_id, lock_id))
            
            self.db.conn.commit()
            return True
        except Exception:
            return False

    async def process_transaction(
        self,
        from_wallet: str,
        to_wallet: str,
        amount: Decimal,
        transaction_type: str = "transfer"
    ) -> Dict[str, Any]:
        """Process a single transaction"""
        transaction_id = str(uuid.uuid4())
        lock_id = str(uuid.uuid4())
        
        try:
            # Acquire locks
            if not await self.acquire_lock(from_wallet, lock_id):
                raise Exception("Could not acquire sender lock")
            if not await self.acquire_lock(to_wallet, lock_id):
                await self.release_lock(from_wallet, lock_id)
                raise Exception("Could not acquire receiver lock")
            
            # Start transaction
            self.db.cursor.execute("""
                INSERT INTO transactions 
                (id, from_wallet, to_wallet, amount, transaction_type, 
                 status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (transaction_id, from_wallet, to_wallet, amount,
                 transaction_type, "pending", datetime.utcnow()))
            
            # Check balance
            self.db.cursor.execute(
                "SELECT balance FROM wallets WHERE id = ?",
                (from_wallet,)
            )
            balance = Decimal(str(self.db.cursor.fetchone()[0]))
            
            if balance < amount:
                raise Exception("Insufficient balance")
            
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
            
            # Record success
            self.db.cursor.execute("""
                UPDATE transactions
                SET status = ?, completed_at = ?
                WHERE id = ?
            """, ("completed", datetime.utcnow(), transaction_id))
            
            self.db.conn.commit()
            
            return {
                "transaction_id": transaction_id,
                "status": "completed",
                "amount": amount
            }
            
        except Exception as e:
            # Record failure
            self.db.cursor.execute("""
                UPDATE transactions
                SET status = ?, error = ?
                WHERE id = ?
            """, ("failed", str(e), transaction_id))
            
            self.db.conn.commit()
            raise
        
        finally:
            # Release locks
            await self.release_lock(from_wallet, lock_id)
            await self.release_lock(to_wallet, lock_id)

    async def test_basic_transactions(self):
        """Test basic transaction functionality"""
        logger.info("Testing basic transactions...")
        
        # Test simple transfer
        from_wallet = self.test_wallets[0]["id"]
        to_wallet = self.test_wallets[1]["id"]
        amount = Decimal("100.0")
        
        result = await self.process_transaction(
            from_wallet, to_wallet, amount
        )
        assert result["status"] == "completed"
        
        # Verify balances
        self.db.cursor.execute(
            "SELECT balance FROM wallets WHERE id = ?",
            (from_wallet,)
        )
        sender_balance = Decimal(str(self.db.cursor.fetchone()[0]))
        assert sender_balance == Decimal("900.0")
        
        self.db.cursor.execute(
            "SELECT balance FROM wallets WHERE id = ?",
            (to_wallet,)
        )
        receiver_balance = Decimal(str(self.db.cursor.fetchone()[0]))
        assert receiver_balance == Decimal("1100.0")

    async def test_concurrent_transactions(self):
        """Test concurrent transaction handling"""
        logger.info("Testing concurrent transactions...")
        
        async def make_concurrent_transfers():
            tasks = []
            for i in range(5):
                from_wallet = self.test_wallets[i]["id"]
                to_wallet = self.test_wallets[(i + 1) % 5]["id"]
                amount = Decimal("10.0")
                
                task = asyncio.create_task(
                    self.process_transaction(
                        from_wallet, to_wallet, amount
                    )
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        
        results = await make_concurrent_transfers()
        
        # Verify all transactions completed
        successful = sum(1 for r in results if isinstance(r, dict) and r["status"] == "completed")
        assert successful > 0, "No concurrent transactions succeeded"
        
        # Verify total balance remained constant
        self.db.cursor.execute("SELECT SUM(balance) FROM wallets")
        total_balance = self.db.cursor.fetchone()[0]
        assert total_balance == Decimal("5000.0"), "Total balance changed"

    async def test_transaction_rollback(self):
        """Test transaction rollback functionality"""
        logger.info("Testing transaction rollback...")
        
        from_wallet = self.test_wallets[0]["id"]
        to_wallet = self.test_wallets[1]["id"]
        
        # Get initial balances
        self.db.cursor.execute(
            "SELECT balance FROM wallets WHERE id IN (?, ?)",
            (from_wallet, to_wallet)
        )
        initial_balances = [Decimal(str(b[0])) for b in self.db.cursor.fetchall()]
        
        # Attempt transaction with insufficient funds
        try:
            await self.process_transaction(
                from_wallet, to_wallet, Decimal("2000.0")
            )
            assert False, "Transaction should have failed"
        except Exception:
            pass
        
        # Verify balances unchanged
        self.db.cursor.execute(
            "SELECT balance FROM wallets WHERE id IN (?, ?)",
            (from_wallet, to_wallet)
        )
        final_balances = [Decimal(str(b[0])) for b in self.db.cursor.fetchall()]
        
        assert initial_balances == final_balances, "Balances changed after failed transaction"

    async def test_transaction_integrity(self):
        """Test transaction data integrity"""
        logger.info("Testing transaction integrity...")
        
        # Create a transaction
        from_wallet = self.test_wallets[0]["id"]
        to_wallet = self.test_wallets[1]["id"]
        amount = Decimal("50.0")
        
        result = await self.process_transaction(
            from_wallet, to_wallet, amount
        )
        
        # Verify transaction record
        self.db.cursor.execute("""
            SELECT id, from_wallet, to_wallet, amount, status
            FROM transactions
            WHERE id = ?
        """, (result["transaction_id"],))
        
        tx_record = self.db.cursor.fetchone()
        assert tx_record is not None
        assert Decimal(str(tx_record[3])) == amount
        assert tx_record[4] == "completed"
        
        # Verify transaction events
        self.db.cursor.execute("""
            SELECT COUNT(*) FROM transaction_events
            WHERE transaction_id = ?
        """, (result["transaction_id"],))
        
        event_count = self.db.cursor.fetchone()[0]
        assert event_count > 0, "No transaction events recorded"

    async def run_all_tests(self):
        """Run all transaction tests"""
        test_methods = [
            self.test_basic_transactions,
            self.test_concurrent_transactions,
            self.test_transaction_rollback,
            self.test_transaction_integrity
        ]
        
        results = []
        for test_method in test_methods:
            try:
                await test_method()
                results.append((test_method.__name__, "PASSED", None))
                logger.info(f"{test_method.__name__} passed")
            except Exception as e:
                results.append((test_method.__name__, "FAILED", str(e)))
                logger.error(f"{test_method.__name__} failed: {str(e)}")
        
        return results

    async def cleanup(self):
        """Cleanup test environment"""
        self.db.cleanup()
        logger.info("Test cleanup complete")

async def run_transaction_tests():
    """Run all transaction tests"""
    test_suite = TransactionTests()
    try:
        await test_suite.setup()
        results = await test_suite.run_all_tests()
        
        # Print results
        print("\nTransaction Test Results:")
        print("========================")
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
        await test_suite.cleanup()

if __name__ == "__main__":
    success = asyncio.run(run_transaction_tests())
    import sys
    sys.exit(0 if success else 1)
