# debug_setup.py

import os
import asyncio
import logging
from dotenv import load_dotenv
import pytest
import uvicorn
from fastapi.testclient import TestClient

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Required environment variables for testing
TEST_ENV_VARS = {
    'DATABASE_URL': 'postgresql://test_user:test_pass@localhost:5432/test_db',
    'SECRET_KEY': 'test_secret_key_123',
    'WEB3_PROVIDER': 'http://localhost:8545',  # Local Ganache instance
    'OPENAI_API_KEY': 'test_openai_key',
    'ANTHROPIC_API_KEY': 'test_anthropic_key',
    'STABILITY_API_KEY': 'test_stability_key',
    'ELEVENLABS_API_KEY': 'test_elevenlabs_key'
}

def setup_test_environment():
    """Setup test environment variables"""
    for key, value in TEST_ENV_VARS.items():
        if key not in os.environ:
            os.environ[key] = value
    
    logger.info("Test environment variables set")

async def test_database_connection():
    """Test database connection"""
    from config.database_manager import DatabaseManager
    
    db_manager = DatabaseManager(os.environ['DATABASE_URL'])
    try:
        await db_manager.initialize()
        health_check = await db_manager.health_check()
        assert health_check['status'] == 'healthy'
        logger.info("Database connection test passed")
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        raise
    finally:
        await db_manager.cleanup()

async def test_api_integrations():
    """Test API integrations"""
    from services.api_integration.openai_api import OpenAIAPI
    from services.api_integration.anthropic_api import AnthropicAPI
    
    apis = [
        ('OpenAI', OpenAIAPI()),
        ('Anthropic', AnthropicAPI())
    ]
    
    for name, api in apis:
        try:
            status = await api.check_status()
            assert status['status'] == 'operational'
            logger.info(f"{name} API test passed")
        except Exception as e:
            logger.error(f"{name} API test failed: {str(e)}")
            raise
        finally:
            await api.cleanup()

def run_unit_tests():
    """Run unit tests"""
    pytest.main(['-v', 'tests/'])

async def test_main_application():
    """Test main application startup"""
    from main import app_manager
    
    try:
        await app_manager.initialize()
        health_check = await app_manager.check_health()
        assert health_check['status'] in ['healthy', 'initializing']
        logger.info("Main application startup test passed")
    except Exception as e:
        logger.error(f"Main application startup test failed: {str(e)}")
        raise
    finally:
        await app_manager.shutdown()

def create_test_client():
    """Create FastAPI test client"""
    from main import app
    return TestClient(app)

async def test_basic_endpoints(client: TestClient):
    """Test basic API endpoints"""
    # Test health endpoint
    response = client.get("/health")
    assert response.status_code == 200
    health_data = response.json()
    assert health_data['status'] in ['healthy', 'initializing']
    logger.info("Health endpoint test passed")
    
    # Test user registration
    test_user = {
        "username": "test_user",
        "email": "test@example.com",
        "password": "Test123!@#",
        "additional_info": {"test": True}
    }
    response = client.post("/api/users/register", json=test_user)
    assert response.status_code in [200, 201]
    logger.info("User registration test passed")

if __name__ == "__main__":
    try:
        # Setup test environment
        setup_test_environment()
        
        # Run tests
        asyncio.run(test_database_connection())
        asyncio.run(test_api_integrations())
        run_unit_tests()
        
        # Test main application
        asyncio.run(test_main_application())
        
        # Test API endpoints
        client = create_test_client()
        asyncio.run(test_basic_endpoints(client))
        
        logger.info("All debug tests completed successfully")
        
        # Start application in debug mode
        if input("Start application server? (y/n): ").lower() == 'y':
            uvicorn.run(
                "main:app",
                host="0.0.0.0",
                port=8000,
                reload=True,
                log_level="debug"
            )
            
    except Exception as e:
        logger.error(f"Debug testing failed: {str(e)}")
        raise
