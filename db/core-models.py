# models/core_models.py

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, 
    ForeignKey, Enum, JSON, Text, Numeric, Table
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from config.database import Base

# Enums
class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    AGENT_CREATOR = "agent_creator"

class AgentStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"

class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# Association Tables
agent_capability = Table(
    'agent_capability',
    Base.metadata,
    Column('agent_id', String(36), ForeignKey('agents.id')),
    Column('capability_id', Integer, ForeignKey('capabilities.id'))
)

# Core Models
class User(Base):
    __tablename__ = 'users'

    id = Column(String(36), primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    created_at = Column(DateTime, server_default=func.now())
    last_active = Column(DateTime, onupdate=func.now())
    is_active = Column(Boolean, default=True)
    preferences = Column(JSON, default={})

    # Relationships
    wallets = relationship("Wallet", back_populates="user")
    agents = relationship("Agent", back_populates="owner")
    transactions = relationship("Transaction", back_populates="user")

class Wallet(Base):
    __tablename__ = 'wallets'

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'))
    address = Column(String(42), unique=True, nullable=False)
    encrypted_key = Column(Text)
    balance = Column(Numeric(precision=36, scale=18), default=0)
    name = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    last_active = Column(DateTime, onupdate=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="wallets")
    transactions = relationship("Transaction", back_populates="wallet")

class Agent(Base):
    __tablename__ = 'agents'

    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), ForeignKey('users.id'))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    status = Column(Enum(AgentStatus), default=AgentStatus.PENDING)
    wallet_address = Column(String(42))
    performance_metrics = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now())
    last_active = Column(DateTime, onupdate=func.now())
    settings = Column(JSON, default={})

    # Relationships
    owner = relationship("User", back_populates="agents")
    capabilities = relationship(
        "Capability",
        secondary=agent_capability,
        back_populates="agents"
    )
    transactions = relationship("Transaction", back_populates="agent")

class Capability(Base):
    __tablename__ = 'capabilities'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    service_type = Column(String(50))  # e.g., "text_generation", "image_generation"
    model_requirements = Column(JSON, default={})
    pricing_tier = Column(String(20))  # e.g., "basic", "premium"

    # Relationships
    agents = relationship(
        "Agent",
        secondary=agent_capability,
        back_populates="capabilities"
    )

class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'))
    wallet_id = Column(String(36), ForeignKey('wallets.id'))
    agent_id = Column(String(36), ForeignKey('agents.id'))
    amount = Column(Numeric(precision=36, scale=18), nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    transaction_type = Column(String(50))  # e.g., "agent_purchase", "token_transfer"
    details = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    error = Column(Text)

    # Relationships
    user = relationship("User", back_populates="transactions")
    wallet = relationship("Wallet", back_populates="transactions")
    agent = relationship("Agent", back_populates="transactions")

class ServiceUsage(Base):
    __tablename__ = 'service_usage'

    id = Column(Integer, primary_key=True)
    agent_id = Column(String(36), ForeignKey('agents.id'))
    service_type = Column(String(50), nullable=False)
    tokens_used = Column(Integer, default=0)
    cost = Column(Numeric(precision=36, scale=18))
    created_at = Column(DateTime, server_default=func.now())
    success = Column(Boolean, default=True)
    response_time = Column(Float)  # in seconds
    error = Column(Text)
    metadata = Column(JSON, default={})

class APIKey(Base):
    __tablename__ = 'api_keys'

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'))
    key_hash = Column(String(255), nullable=False)
    name = Column(String(50))
    permissions = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime)
    use_count = Column(Integer, default=0)

# Create indexes for better query performance
from sqlalchemy import Index

# User indexes
Index('idx_users_email', User.email)
Index('idx_users_username', User.username)

# Wallet indexes
Index('idx_wallets_address', Wallet.address)
Index('idx_wallets_user', Wallet.user_id)

# Agent indexes
Index('idx_agents_owner', Agent.owner_id)
Index('idx_agents_status', Agent.status)

# Transaction indexes
Index('idx_transactions_user', Transaction.user_id)
Index('idx_transactions_status', Transaction.status)
Index('idx_transactions_created', Transaction.created_at)

# Service usage indexes
Index('idx_usage_agent', ServiceUsage.agent_id)
Index('idx_usage_type', ServiceUsage.service_type)
Index('idx_usage_created', ServiceUsage.created_at)

# Initialize database function
def init_db(engine):
    """Initialize database with tables and initial data"""
    Base.metadata.create_all(bind=engine)
    
    # Add initial capabilities if needed
    return True

# Database session context manager
from contextlib import contextmanager
from sqlalchemy.orm import Session

@contextmanager
def get_db_session(engine) -> Session:
    """Get database session with automatic cleanup"""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
