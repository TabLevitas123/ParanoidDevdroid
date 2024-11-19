# run_tests.py

import asyncio
import logging
from pathlib import Path
from typing import Optional
import sys

from tests.test_config import setup_test_env, TEST_CONFIG, TestData
from db_init_sequence import DatabaseManager
from utils.logger import CustomLogger

# Configure logging
logger = CustomLogger("test_runner", "tests.log")

class TestRunner:
    """Manages test execution and environment setup"""
    
    def __init__(self):
        self.db_manager: Optional[DatabaseManager] = None
        self.test_data = TestData()
        
    async def setup(self):
        """Setup test environment"""
        try:
            logger.info("Setting up test environment...")
            
            # Setup test environment variables
            setup_test_env()
            
            # Initialize database
            self.db_manager = DatabaseManager(TEST_CONFIG["database"]["url"])
            await self.db_manager.initialize()
            
            logger.info("Test environment setup complete")
            return True
            
        except Exception as e:
            logger.error(f"Test setup failed: {str(e)}")
            raise
    
    async def run_tests(self):
        """Run all tests"""
        try:
            logger.info("Running tests...")
            
            # Test database operations
            await self._test_database()
            
            # Test user operations
            await self._test_user_operations()
            
            # Test agent operations
            await self._test_agent_operations()
            
            # Test wallet operations
            await self._test_wallet_operations()
            
            logger.info("All tests completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Tests failed: {str(e)}")
            return False
    
    async def _test_database(self):
        """Test database operations"""
        logger.info("Testing database operations...")
        
        async for session in self.db_manager.get_session():
            # Test simple query
            result = await session.execute("SELECT 1")
            assert result is not None
            
        logger.info("Database tests passed")
    
    async def _test_user_operations(self):
        """Test user operations"""
        logger.info("Testing user operations...")
        
        # Import here to avoid circular imports
        from models.core_models import User
        from schemas.core_schemas import UserCreate
        
        # Create test user
        test_user_data = self.test_data.get_test_user()
        user_create = UserCreate(**test_user_data)
        
        async for session in self.db_manager.get_session():
            # Create user
            user = User(
                username=user_create.username,
                email=user_create.email,
                password_hash="test_hash"  # In real app, would be hashed
            )
            session.add(user)
            await session.commit()
            
            # Query user
            result = await session.execute(
                "SELECT * FROM users WHERE email = :email",
                {"email": user_create.email}
            )
            fetched_user = result.first()
            assert fetched_user is not None
            
        logger.info("User operation tests passed")
    
    async def _test_agent_operations(self):
        """Test agent operations"""
        logger.info("Testing agent operations...")
        
        # Import here to avoid circular imports
        from models.core_models import Agent
        from schemas.core_schemas import AgentCreate
        
        # Create test agent
        test_agent_data = self.test_data.get_test_agent()
        agent_create = AgentCreate(**test_agent_data)
        
        async for session in self.db_manager.get_session():
            # Create agent
            agent = Agent(
                name=agent_create.name,
                description=agent_create.description,
                owner_id="test_user_id"  # Would be real user ID in production
            )
            session.add(agent)
            await session.commit()
            
            # Query agent
            result = await session.execute(
                "SELECT * FROM agents WHERE name = :name",
                {"name": agent_create.name}
            )
            fetched_agent = result.first()
            assert fetched_agent is not None
            
        logger.info("Agent operation tests passed")
    
    async def _test_wallet_operations(self):
        """Test wallet operations"""
        logger.info("Testing wallet operations...")
        
        # Import here to avoid circular imports
        from models.core_models import Wallet
        from schemas.core_schemas import WalletCreate
        
        # Create test wallet
        test_wallet_data = self.test_data.get_test_wallet()
        wallet_create = WalletCreate(**test_wallet_data)
        
        async for session in self.db_manager.get_session():
            # Create wallet
            wallet = Wallet(
                name=wallet_create.name,
                address="0x123",  # Would be real address in production
                user_id="test_user_id"  # Would be real user ID in production
            )
            session.add(wallet)
            await session.commit()
            
            # Query wallet
            result = await session.execute(
                "SELECT * FROM wallets WHERE name = :name",
                {"name": wallet_create.name}
            )
            fetched_wallet = result.first()
            assert fetched_wallet is not None
            
        logger.info("Wallet operation tests passed")
    
    async def cleanup(self):
        """Cleanup test environment"""
        try:
            logger.info("Cleaning up test environment...")
            
            if self.db_manager:
                await self.db_manager.cleanup()
                
            logger.info("Cleanup complete")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise

async def main():
    """Main test execution"""
    runner = TestRunner()
    try:
        # Setup
        await runner.setup()
        
        # Run tests
        success = await runner.run_tests()
        
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
        await runner.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
