# tests/api_endpoint_tests.py

import pytest
from fastapi.testclient import TestClient
import json
from datetime import datetime
import uuid
from typing import Dict, Any, Generator

from tests.test_db import TestDatabase
from tests.test_config import TestData
from utils.logger import CustomLogger
from main import app  # Import your FastAPI app

logger = CustomLogger("api_tests", "api_tests.log")

class APITestClient:
    """Test client for API endpoints"""
    
    def __init__(self):
        self.client = TestClient(app)
        self.db = TestDatabase()
        self.test_data = TestData()
        self.auth_tokens: Dict[str, str] = {}
    
    async def setup(self):
        """Setup test environment"""
        self.db.setup()
        
    async def cleanup(self):
        """Cleanup test environment"""
        self.db.cleanup()

    async def register_test_user(self) -> Dict[str, Any]:
        """Register a test user and return credentials"""
        user_data = self.test_data.get_test_user()
        response = self.client.post(
            "/api/users/register",
            json=user_data
        )
        assert response.status_code == 200
        return {
            "user_data": user_data,
            "response": response.json()
        }

    async def login_test_user(self, email: str, password: str) -> str:
        """Login test user and return auth token"""
        response = self.client.post(
            "/api/users/login",
            json={
                "email": email,
                "password": password,
                "device_info": {"device": "test_device"}
            }
        )
        assert response.status_code == 200
        return response.json()["token"]

    def get_auth_headers(self, token: str) -> Dict[str, str]:
        """Get headers with authentication"""
        return {"Authorization": f"Bearer {token}"}

class APIEndpointTests:
    """Test cases for API endpoints"""
    
    def __init__(self):
        self.api = APITestClient()
        self.test_user: Dict[str, Any] = {}
        self.auth_token: str = ""
    
    async def setup(self):
        """Setup test environment"""
        await self.api.setup()
        user_info = await self.api.register_test_user()
        self.test_user = user_info["user_data"]
        self.auth_token = await self.api.login_test_user(
            self.test_user["email"],
            self.test_user["password"]
        )
    
    async def cleanup(self):
        """Cleanup test environment"""
        await self.api.cleanup()

    async def test_user_endpoints(self):
        """Test user-related endpoints"""
        logger.info("Testing user endpoints...")
        
        # Test user registration
        new_user = {
            "username": f"test_user_{uuid.uuid4().hex[:8]}",
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "password": "Test123!@#",
            "additional_info": {"test": True}
        }
        
        response = self.api.client.post(
            "/api/users/register",
            json=new_user
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Test user login
        response = self.api.client.post(
            "/api/users/login",
            json={
                "email": new_user["email"],
                "password": new_user["password"],
                "device_info": {"device": "test"}
            }
        )
        assert response.status_code == 200
        assert "token" in response.json()
        
        # Test get user profile
        headers = self.api.get_auth_headers(response.json()["token"])
        response = self.api.client.get(
            "/api/users/profile",
            headers=headers
        )
        assert response.status_code == 200
        assert response.json()["email"] == new_user["email"]
        
        # Test update user profile
        update_data = {
            "username": f"updated_user_{uuid.uuid4().hex[:8]}"
        }
        response = self.api.client.put(
            "/api/users/profile",
            headers=headers,
            json=update_data
        )
        assert response.status_code == 200
        assert response.json()["username"] == update_data["username"]

    async def test_wallet_endpoints(self):
        """Test wallet-related endpoints"""
        logger.info("Testing wallet endpoints...")
        
        headers = self.api.get_auth_headers(self.auth_token)
        
        # Test create wallet
        wallet_data = {
            "name": "Test Wallet",
            "initial_balance": 1000.0
        }
        response = self.api.client.post(
            "/api/wallets",
            headers=headers,
            json=wallet_data
        )
        assert response.status_code == 200
        wallet_id = response.json()["wallet"]["id"]
        
        # Test get wallet
        response = self.api.client.get(
            f"/api/wallets/{wallet_id}",
            headers=headers
        )
        assert response.status_code == 200
        assert response.json()["name"] == wallet_data["name"]
        
        # Test list wallets
        response = self.api.client.get(
            "/api/wallets",
            headers=headers
        )
        assert response.status_code == 200
        assert len(response.json()["wallets"]) > 0
        
        # Test wallet balance
        response = self.api.client.get(
            f"/api/wallets/{wallet_id}/balance",
            headers=headers
        )
        assert response.status_code == 200
        assert float(response.json()["balance"]) == wallet_data["initial_balance"]

    async def test_agent_endpoints(self):
        """Test agent-related endpoints"""
        logger.info("Testing agent endpoints...")
        
        headers = self.api.get_auth_headers(self.auth_token)
        
        # Test create agent
        agent_data = {
            "name": "Test Agent",
            "description": "A test AI agent",
            "capabilities": ["text_generation"],
            "initial_balance": 100.0
        }
        response = self.api.client.post(
            "/api/agents",
            headers=headers,
            json=agent_data
        )
        assert response.status_code == 200
        agent_id = response.json()["agent"]["id"]
        
        # Test get agent
        response = self.api.client.get(
            f"/api/agents/{agent_id}",
            headers=headers
        )
        assert response.status_code == 200
        assert response.json()["name"] == agent_data["name"]
        
        # Test list agents
        response = self.api.client.get(
            "/api/agents",
            headers=headers
        )
        assert response.status_code == 200
        assert len(response.json()["agents"]) > 0
        
        # Test update agent
        update_data = {
            "name": "Updated Agent",
            "description": "Updated description"
        }
        response = self.api.client.put(
            f"/api/agents/{agent_id}",
            headers=headers,
            json=update_data
        )
        assert response.status_code == 200
        assert response.json()["name"] == update_data["name"]

    async def test_marketplace_endpoints(self):
        """Test marketplace-related endpoints"""
        logger.info("Testing marketplace endpoints...")
        
        headers = self.api.get_auth_headers(self.auth_token)
        
        # Create agent for listing
        agent_response = self.api.client.post(
            "/api/agents",
            headers=headers,
            json={
                "name": "Agent for Sale",
                "description": "Test agent for marketplace",
                "capabilities": ["text_generation"],
                "initial_balance": 100.0
            }
        )
        agent_id = agent_response.json()["agent"]["id"]
        
        # Test create listing
        listing_data = {
            "agent_id": agent_id,
            "price": 500.0,
            "description": "Test listing",
            "tags": ["test", "ai"],
            "duration_days": 7
        }
        response = self.api.client.post(
            "/api/marketplace/listings",
            headers=headers,
            json=listing_data
        )
        assert response.status_code == 200
        listing_id = response.json()["listing"]["id"]
        
        # Test get listing
        response = self.api.client.get(
            f"/api/marketplace/listings/{listing_id}",
            headers=headers
        )
        assert response.status_code == 200
        assert response.json()["price"] == listing_data["price"]
        
        # Test search listings
        response = self.api.client.get(
            "/api/marketplace/listings",
            params={"query": "test", "min_price": 100, "max_price": 1000}
        )
        assert response.status_code == 200
        assert len(response.json()["listings"]) > 0
        
        # Test update listing
        update_data = {
            "price": 450.0,
            "description": "Updated listing"
        }
        response = self.api.client.put(
            f"/api/marketplace/listings/{listing_id}",
            headers=headers,
            json=update_data
        )
        assert response.status_code == 200
        assert response.json()["price"] == update_data["price"]

    async def test_ai_service_endpoints(self):
        """Test AI service-related endpoints"""
        logger.info("Testing AI service endpoints...")
        
        headers = self.api.get_auth_headers(self.auth_token)
        
        # Test text generation
        text_request = {
            "prompt": "Write a test message",
            "max_tokens": 50,
            "model": "gpt-3.5-turbo"
        }
        response = self.api.client.post(
            "/api/services/generate-text",
            headers=headers,
            json=text_request
        )
        assert response.status_code == 200
        assert "text" in response.json()
        
        # Test model status
        response = self.api.client.get(
            "/api/services/status",
            headers=headers
        )
        assert response.status_code == 200
        assert "models" in response.json()

    async def run_all_tests(self):
        """Run all API endpoint tests"""
        test_methods = [
            self.test_user_endpoints,
            self.test_wallet_endpoints,
            self.test_agent_endpoints,
            self.test_marketplace_endpoints,
            self.test_ai_service_endpoints
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

async def run_api_tests():
    """Run all API tests"""
    test_suite = APIEndpointTests()
    try:
        await test_suite.setup()
        results = await test_suite.run_all_tests()
        
        # Print results
        print("\nAPI Endpoint Test Results:")
        print("=========================")
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
    import asyncio
    success = asyncio.run(run_api_tests())
    import sys
    sys.exit(0 if success else 1)
