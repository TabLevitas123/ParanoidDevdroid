# config/database_models.py

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, 
    DateTime, ForeignKey, Enum, JSON, Text,
    Numeric, Table
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

# Association tables for many-to-many relationships
agent_category_association = Table(
    'agent_categories',
    Base.metadata,
    Column('agent_id', String(36), ForeignKey('agents.id')),
    Column('category_id', Integer, ForeignKey('categories.id'))
)

listing_tag_association = Table(
    'listing_tags',
    Base.metadata,
    Column('listing_id', String(36), ForeignKey('listings.id')),
    Column('tag_id', Integer, ForeignKey('tags.id'))
)

class UserRole(enum.Enum):
    USER = "user"
    AGENT_CREATOR = "agent_creator"
    ADMIN = "admin"

class AgentStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"

class ListingStatus(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    SOLD = "sold"
    EXPIRED = "expired"
    DELETED = "deleted"

class TransactionStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    DISPUTED = "disputed"

class User(Base):
    __tablename__ = 'users'

    id = Column(String(36), primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    preferences = Column(JSON)
    
    # Relationships
    wallets = relationship("Wallet", back_populates="user")
    agents = relationship("Agent", back_populates="owner")
    listings = relationship("Listing", back_populates="seller")
    transactions_as_buyer = relationship(
        "Transaction",
        foreign_keys="Transaction.buyer_id",
        back_populates="buyer"
    )
    transactions_as_seller = relationship(
        "Transaction",
        foreign_keys="Transaction.seller_id",
        back_populates="seller"
    )

class Wallet(Base):
    __tablename__ = 'wallets'

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'))
    address = Column(String(42), unique=True, nullable=False)
    name = Column(String(50))
    encrypted_key = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="wallets")
    balances = relationship("WalletBalance", back_populates="wallet")

class WalletBalance(Base):
    __tablename__ = 'wallet_balances'

    id = Column(Integer, primary_key=True)
    wallet_id = Column(String(36), ForeignKey('wallets.id'))
    token_type = Column(String(20), nullable=False)
    balance = Column(Numeric(precision=36, scale=18), default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    wallet = relationship("Wallet", back_populates="balances")

class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    parent_id = Column(Integer, ForeignKey('categories.id'))
    
    # Self-referential relationship for hierarchical categories
    subcategories = relationship("Category")

class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)

class Agent(Base):
    __tablename__ = 'agents'

    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), ForeignKey('users.id'))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    status = Column(Enum(AgentStatus), default=AgentStatus.PENDING)
    capabilities = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    wallet_address = Column(String(42))
    performance_metrics = Column(JSON)
    
    # Relationships
    owner = relationship("User", back_populates="agents")
    categories = relationship(
        "Category",
        secondary=agent_category_association
    )
    listings = relationship("Listing", back_populates="agent")
    transactions = relationship("Transaction", back_populates="agent")

class Listing(Base):
    __tablename__ = 'listings'

    id = Column(String(36), primary_key=True)
    agent_id = Column(String(36), ForeignKey('agents.id'))
    seller_id = Column(String(36), ForeignKey('users.id'))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    price = Column(Numeric(precision=36, scale=18), nullable=False)
    status = Column(Enum(ListingStatus), default=ListingStatus.DRAFT)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    views = Column(Integer, default=0)
    favorites_count = Column(Integer, default=0)
    
    # Relationships
    agent = relationship("Agent", back_populates="listings")
    seller = relationship("User", back_populates="listings")
    tags = relationship("Tag", secondary=listing_tag_association)
    transaction = relationship("Transaction", back_populates="listing", uselist=False)
    favorites = relationship("ListingFavorite", back_populates="listing")

class ListingFavorite(Base):
    __tablename__ = 'listing_favorites'

    id = Column(Integer, primary_key=True)
    listing_id = Column(String(36), ForeignKey('listings.id'))
    user_id = Column(String(36), ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    listing = relationship("Listing", back_populates="favorites")

class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(String(36), primary_key=True)
    buyer_id = Column(String(36), ForeignKey('users.id'))
    seller_id = Column(String(36), ForeignKey('users.id'))
    agent_id = Column(String(36), ForeignKey('agents.id'))
    listing_id = Column(String(36), ForeignKey('listings.id'))
    amount = Column(Numeric(precision=36, scale=18), nullable=False)
    fee = Column(Numeric(precision=36, scale=18), nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    error = Column(Text)
    dispute_data = Column(JSON)
    
    # Relationships
    buyer = relationship(
        "User",
        foreign_keys=[buyer_id],
        back_populates="transactions_as_buyer"
    )
    seller = relationship(
        "User",
        foreign_keys=[seller_id],
        back_populates="transactions_as_seller"
    )
    agent = relationship("Agent", back_populates="transactions")
    listing = relationship("Listing", back_populates="transaction")

class APIKey(Base):
    __tablename__ = 'api_keys'

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'))
    service = Column(String(50), nullable=False)
    encrypted_key = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    is_active = Column(Boolean, default=True)

class ServiceUsage(Base):
    __tablename__ = 'service_usage'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'))
    service = Column(String(50), nullable=False)
    request_type = Column(String(50), nullable=False)
    tokens_used = Column(Integer)
    cost = Column(Numeric(precision=36, scale=18))
    timestamp = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean, default=True)
    error = Column(Text)
    metadata = Column(JSON)

class SystemMetrics(Base):
    __tablename__ = 'system_metrics'

    id = Column(Integer, primary_key=True)
    metric_type = Column(String(50), nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON)

class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'))
    action = Column(String(50), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(String(36))
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(String(255))

# Index creation helper function
def create_indexes(engine):
    """Create database indexes for optimal query performance"""
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
    
    # Listing indexes
    Index('idx_listings_seller', Listing.seller_id)
    Index('idx_listings_status', Listing.status)
    Index('idx_listings_price', Listing.price)
    
    # Transaction indexes
    Index('idx_transactions_buyer', Transaction.buyer_id)
    Index('idx_transactions_seller', Transaction.seller_id)
    Index('idx_transactions_status', Transaction.status)
    Index('idx_transactions_created', Transaction.created_at)
    
    # Service usage indexes
    Index('idx_service_usage_user', ServiceUsage.user_id)
    Index('idx_service_usage_service', ServiceUsage.service)
    Index('idx_service_usage_timestamp', ServiceUsage.timestamp)
    
    # Audit log indexes
    Index('idx_audit_logs_user', AuditLog.user_id)
    Index('idx_audit_logs_action', AuditLog.action)
    Index('idx_audit_logs_timestamp', AuditLog.timestamp)
