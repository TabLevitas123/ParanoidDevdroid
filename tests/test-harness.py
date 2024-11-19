# test_harness.py

import asyncio
import logging
from typing import Dict, Any
from datetime import datetime
from mock_blockchain import mock_blockchain
from test_db_manager import TestDatabaseManager
from setup_env import setup_test_env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestHarness:
    """Test harness for running and debugging the application"""
    
    def __init__(self):
        self.db = None
        self.app = None
        self.client = None
        self.test_user_token = None
        self.test_user_data = None
        
    async def setup(self):
        """Setup test environment"""
        try:
            logger.info("Setting up test environment...")
            
            # Setup environment variables
            setup_test_env()
            
            # Initialize test database
            self.db = TestDatabaseManager()
            await self.db.initialize()
            
            # Import and initialize application
            from main import app_manager, app
            self.app = app
            await app_manager.initialize()
            
            # Setup test client
            from fastapi.testclient import TestClient
            self.client = TestClient(self.app)
            
            logger.info("Test environment setup complete")
            return True
            
        except Exception as e:
            logger.error(f"Setup failed: {str(e)}")
            raise

    async def run_basic_tests(self):
        """Run basic functionality tests"""
        try:
            # Test health endpoint
            logger.info("Testing health endpoint...")
            response = self.client.get("/health")
            assert response.status_code == 200
            assert response.json()['status'] in ['healthy', 'initializing']
            
            # Test user registration
            await self._test_user_registration()
            
            # Test user login
            await self._test_user_login()
            
            # Test wallet creation
            await self._test_wallet_creation()
            
            # Test agent creation
            await self._test_agent_creation()
            
            # Test marketplace functionality
            await self._test_marketplace()
            
            logger.info("Basic tests completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            return False

    async def _test_user_registration(self):
        """Test user registration"""
        logger.info("Testing user registration...")
        
        self.test_user_data = {
            "username": f"test_user_{datetime.now().timestamp()}",
            "email": f"test_{datetime.now().timestamp()}@example.com",
            "password": "Test123!@#",
            "additional_info": {"test": True}
        }
        
        response = self.client.post("/api/users/register", json=self.test_user_data)
        assert response.status_code in [200, 201]
        
        user_response = response.json()
        assert user_response['success'] is True
        assert 'user' in user_response
        
        logger.info("User registration successful")
        return user_response['user']

    async def _test_user_login(self):
        """Test user login"""
        logger.info("Testing user login...")
        
        login_data = {
            "email": self.test_user_data["email"],
            "password": self.test_user_data["password"],
            "device_info": {"device": "test_device"}
        }
        
        response = self.client.post("/api/users/login", json=login_data)
        assert response.status_code == 200
        
        login_response = response.json()
        assert login_response['success'] is True
        assert 'token' in login_response
        
        self.test_user_token = login_response['token']
        logger.info("User login successful")
        return login_response

    async def _test_wallet_creation(self):
        """Test wallet creation and management"""
        logger.info("Testing wallet creation...")
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        
        # Create wallet
        response = self.client.post(
            "/api/wallets",
            headers=headers,
            json={"name": "Test Wallet"}
        )
        assert response.status_code == 200
        
        wallet_data = response.json()
        assert wallet_data['success'] is True
        assert 'wallet' in wallet_data
        
        # Test wallet balance
        response = self.client.get(
            f"/api/wallets/{wallet_data['wallet']['id']}/balance",
            headers=headers
        )
        assert response.status_code == 200
        
        logger.info("Wallet tests successful")
        return wallet_data['wallet']

    async def _test_agent_creation(self):
        """Test agent creation and management"""
        logger.info("Testing agent creation...")
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        
        agent_data = {
            "name": "Test Agent",
            "description": "A test AI agent",
            "capabilities": ["text_generation"],
            "initial_balance": 100
        }
        
        response = self.client.post(
            "/api/agents",
            headers=headers,
            json=agent_data
        )
        assert response.status_code == 200
        
        agent_response = response.json()
        assert agent_response['success'] is True
        assert 'agent' in agent_response
        
        logger.info("Agent creation successful")
        return agent_response['agent']

    async def _test_marketplace(self):
        """Test marketplace functionality"""
        logger.info("Testing marketplace functionality...")
        
        headers = {"Authorization": f"Bearer {self.test_user_token}"}
        
        # Create agent listing
        listing_data = {
            "agent_id": (await self._test_agent_creation())['id'],
            "price": 100,
            "description": "Test listing",
            "duration_days": 7
        }
        
        response = self.client.post(
            "/api/marketplace/listings",
            headers=headers,
            json=listing_data
        )
        assert response.status_code == 200
        
        listing_response = response.json()
        assert listing_response['success'] is True
        assert 'listing' in listing_response
        
        # Search listings
        response = self.client.get(
            "/api/marketplace/listings",
            headers=headers,
            params={"query": "Test"}
        )
        assert response.status_code == 200
        
        logger.info("Marketplace tests successful")
        return listing_response['listing']

    async def cleanup(self):
        """Cleanup test environment"""
        try:
            logger.info("Cleaning up test environment...")
            
            # Cleanup database
            if self.db:
                await self.db.cleanup()
            
            # Cleanup application
            from main import app_manager
            await app_manager.shutdown()
            
            logger.info("Cleanup complete")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise

async def main():
    """Main test runner"""
    harness = TestHarness()
    try:
        await harness.setup()
        success = await harness.run_basic_tests()
        
        if success:
            logger.info("All tests passed!")
        else:
            logger.error("Some tests failed!")
            
    except Exception as e:
        logger.error(f"Test harness failed: {str(e)}")
        raise
    finally:
        await harness.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
