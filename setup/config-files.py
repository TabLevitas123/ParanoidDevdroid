# config/constants.py
from enum import Enum

class AgentStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"

class TokenType(Enum):
    MAIN = "main"
    UTILITY = "utility"
    GOVERNANCE = "governance"

class TransactionStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# API endpoints and configuration
API_CONFIG = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4", "gpt-3.5-turbo"],
        "timeout": 30
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "models": ["claude-2", "claude-instant"],
        "timeout": 30
    },
    "stability": {
        "base_url": "https://api.stability.ai/v1",
        "timeout": 60
    },
    "elevenlabs": {
        "base_url": "https://api.elevenlabs.io/v1",
        "timeout": 30
    }
}

# System configuration
SYSTEM_CONFIG = {
    "max_retries": 3,
    "retry_delay": 1,  # seconds
    "batch_size": 100,
    "cache_ttl": 3600,  # seconds
    "max_concurrent_tasks": 50
}

# Error codes and messages
ERROR_CODES = {
    "AGENT_001": "Agent creation failed",
    "AGENT_002": "Agent not found",
    "TOKEN_001": "Insufficient balance",
    "TOKEN_002": "Invalid token type",
    "MARKET_001": "Listing creation failed",
    "MARKET_002": "Invalid listing status",
    "API_001": "API request failed",
    "API_002": "Rate limit exceeded"
}

# config/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
import os

Base = declarative_base()

class DatabaseConfig:
    def __init__(self):
        self.connection_url = os.getenv(
            'DATABASE_URL',
            'postgresql://user:password@localhost:5432/ai_platform'
        )
        self.engine = create_engine(
            self.connection_url,
            poolclass=QueuePool,
            pool_size=20,
            max_overflow=30,
            pool_timeout=30,
            pool_recycle=1800
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

    def get_db(self):
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)

# config/api_keys.py
import os
from cryptography.fernet import Fernet
from typing import Dict

class APIKeyManager:
    def __init__(self):
        self.encryption_key = os.getenv('ENCRYPTION_KEY', Fernet.generate_key())
        self.cipher_suite = Fernet(self.encryption_key)
        
    def _encrypt(self, text: str) -> bytes:
        return self.cipher_suite.encrypt(text.encode())
    
    def _decrypt(self, encrypted_text: bytes) -> str:
        return self.cipher_suite.decrypt(encrypted_text).decode()
    
    def load_api_keys(self) -> Dict[str, str]:
        """Load and decrypt API keys from environment variables"""
        api_keys = {
            'openai': os.getenv('OPENAI_API_KEY'),
            'anthropic': os.getenv('ANTHROPIC_API_KEY'),
            'stability': os.getenv('STABILITY_API_KEY'),
            'elevenlabs': os.getenv('ELEVENLABS_API_KEY')
        }
        
        # Encrypt keys for secure storage
        encrypted_keys = {
            service: self._encrypt(key) if key else None
            for service, key in api_keys.items()
        }
        
        return encrypted_keys
    
    def get_api_key(self, service: str) -> str:
        """Retrieve and decrypt API key for specified service"""
        encrypted_keys = self.load_api_keys()
        if service not in encrypted_keys or not encrypted_keys[service]:
            raise ValueError(f"No API key found for service: {service}")
        return self._decrypt(encrypted_keys[service])

# config/settings.py
import os
from typing import Any, Dict
from pydantic import BaseSettings, SecretStr

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "AI Agent Platform"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # Security settings
    SECRET_KEY: SecretStr = SecretStr(os.urandom(32).hex())
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database settings
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/ai_platform"
    
    # Redis settings for caching
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # API rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 3600  # seconds
    
    # Agent settings
    MAX_AGENTS_PER_USER: int = 10
    AGENT_TASK_TIMEOUT: int = 300  # seconds
    
    # Token economics
    INITIAL_TOKEN_SUPPLY: int = 1000000
    MIN_STAKE_AMOUNT: int = 100
    
    # Marketplace settings
    MARKETPLACE_FEE_PERCENTAGE: float = 2.5
    MIN_LISTING_PRICE: float = 1.0
    
    class Config:
        case_sensitive = True
        env_file = ".env"

    @classmethod
    def get_settings(cls) -> "Settings":
        return cls()

    def get_api_settings(self) -> Dict[str, Any]:
        """Get API-specific settings"""
        return {
            "openai": {
                "timeout": 30,
                "max_retries": 3,
                "backoff_factor": 0.5
            },
            "anthropic": {
                "timeout": 30,
                "max_retries": 3,
                "backoff_factor": 0.5
            },
            "stability": {
                "timeout": 60,
                "max_retries": 2,
                "backoff_factor": 1.0
            },
            "elevenlabs": {
                "timeout": 30,
                "max_retries": 2,
                "backoff_factor": 0.5
            }
        }

settings = Settings.get_settings()
