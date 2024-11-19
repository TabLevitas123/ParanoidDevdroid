# __init__.py files for each package

# models/__init__.py
from .core_models import (
    Base, User, Wallet, Agent, Transaction,
    UserRole, AgentStatus, TransactionStatus
)

# schemas/__init__.py
from .core_schemas import (
    UserCreate, UserLogin, UserUpdate, UserResponse,
    WalletCreate, WalletResponse,
    AgentCreate, AgentUpdate, AgentResponse,
    TransactionCreate, TransactionResponse
)

# utils/__init__.py
from .logger import CustomLogger
from .error_handler import CustomException, handle_exceptions

# tests/__init__.py
from .test_config import TEST_CONFIG, TestData, setup_test_env

# config/__init__.py
from .database import DatabaseManager
