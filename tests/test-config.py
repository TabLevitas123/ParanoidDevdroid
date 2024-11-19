# tests/test_config.py

import os
from pathlib import Path
from typing import Dict, Any

# Test configuration
TEST_CONFIG = {
    "database": {
        "url": "sqlite:///./test/db/test.db",  # Changed to sync URL for testing
        "async_url": "sqlite+aiosqlite:///./test/db/test.db",
        "test_user": "test_user",
        "test_password": "test_password"
    },
    "auth": {
        "secret_key": "test_secret_key_123",
        "algorithm": "HS256",
        "access_token_expire_minutes": 30
    },
    "api": {
        "openai_key": "test_openai_key",
        "anthropic_key": "test_anthropic_key",
        "stability_key": "test_stability_key",
        "elevenlabs_key": "test_elevenlabs_key"
    }
}

def setup_test_env():
    """Setup test environment"""
    # Create test directories
    for dir_path in ["test/db", "test/logs", "test/data"]:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    # Set environment variables
    os.environ.update({
        "TESTING": "true",
        "DATABASE_URL": TEST_CONFIG["database"]["url"],
        "DATABASE_ASYNC_URL": TEST_CONFIG["database"]["async_url"],
        "SECRET_KEY": TEST_CONFIG["auth"]["secret_key"],
        "ENVIRONMENT": "test",
        
        # API Keys
        "OPENAI_API_KEY": TEST_CONFIG["api"]["openai_key"],
        "ANTHROPIC_API_KEY": TEST_CONFIG["api"]["anthropic_key"],
        "STABILITY_API_KEY": TEST_CONFIG["api"]["stability_key"],
        "ELEVENLABS_API_KEY": TEST_CONFIG["api"]["elevenlabs_key"]
    })

# Test data
class TestData:
    @staticmethod
    def get_test_user() -> Dict[str, Any]:
        return {
            "username": "test_user",
            "email": "test@example.com",
            "password": "Test123!@#",
            "additional_info": {"test": True}
        }

    @staticmethod
    def get_test_agent() -> Dict[str, Any]:
        return {
            "name": "Test Agent",
            "description": "A test agent",
            "capabilities": ["text_generation"],
            "initial_balance": 100.0
        }

    @staticmethod
    def get_test_wallet() -> Dict[str, Any]:
        return {
            "name": "Test Wallet",
            "initial_balance": 1000.0
        }

if __name__ == "__main__":
    setup_test_env()
    print("Test environment setup complete")
