# quick_test.py

import asyncio
import logging
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_test():
    """Run basic functionality test"""
    try:
        # Import our main app
        from main import app_manager, app
        client = TestClient(app)
        
        # Initialize application
        logger.info("Initializing application...")
        await app_manager.initialize()
        
        # Test basic API functionality
        logger.info("Testing health endpoint...")
        response = client.get("/health")
        assert response.status_code == 200
        logger.info(f"Health check response: {response.json()}")
        
        # Test user registration
        test_user = {
            "username": "test_user",
            "email": "test@example.com",
            "password": "Test123!@#",
            "additional_info": {"test": True}
        }
        
        logger.info("Testing user registration...")
        response = client.post("/api/users/register", json=test_user)
        assert response.status_code in [200, 201]
        user_data = response.json()
        logger.info(f"User registration response: {user_data}")
        
        # Test user login
        login_data = {
            "email": "test@example.com",
            "password": "Test123!@#",
            "device_info": {"device": "test"}
        }
        
        logger.info("Testing user login...")
        response = client.post("/api/users/login", json=login_data)
        assert response.status_code == 200
        token_data = response.json()
        logger.info("Login successful")
        
        # Get auth token for subsequent requests
        auth_token = token_data['token']
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Test getting user profile
        logger.info("Testing profile retrieval...")
        response = client.get("/api/users/profile", headers=headers)
        assert response.status_code == 200
        profile_data = response.json()
        logger.info(f"Profile data: {profile_data}")
        
        # Test wallet creation
        logger.info("Testing wallet creation...")
        response = client.post("/api/wallets", headers=headers)
        assert response.status_code == 200
        wallet_data = response.json()
        logger.info(f"Wallet data: {wallet_data}")
        
        # Test creating an agent
        agent_data = {
            "name": "Test Agent",
            "description": "A test agent",
            "capabilities": ["text_generation"]
        }
        
        logger.info("Testing agent creation...")
        response = client.post("/api/agents", json=agent_data, headers=headers)
        assert response.status_code == 200
        agent_data = response.json()
        logger.info(f"Agent data: {agent_data}")
        
        logger.info("All basic functionality tests passed!")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise
    finally:
        # Cleanup
        await app_manager.shutdown()

if __name__ == "__main__":
    asyncio.run(run_test())
