# schemas/core_schemas.py

from pydantic import BaseModel, EmailStr, constr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

class UserBase(BaseModel):
    username: constr(min_length=3, max_length=50)
    email: EmailStr

class UserCreate(UserBase):
    password: constr(min_length=8)
    additional_info: Optional[Dict[str, Any]] = None

    @validator('password')
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    device_info: Optional[Dict[str, str]] = None

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    preferences: Optional[Dict[str, Any]] = None

class UserResponse(UserBase):
    id: str
    role: str
    created_at: datetime
    last_active: Optional[datetime]
    is_active: bool
    preferences: Dict[str, Any]

    class Config:
        orm_mode = True

class WalletBase(BaseModel):
    name: Optional[str] = None

class WalletCreate(WalletBase):
    pass

class WalletResponse(WalletBase):
    id: str
    address: str
    balance: Decimal
    created_at: datetime
    last_active: Optional[datetime]
    is_active: bool

    class Config:
        orm_mode = True

class AgentBase(BaseModel):
    name: constr(min_length=1, max_length=100)
    description: Optional[str] = None
    capabilities: List[str] = []

class AgentCreate(AgentBase):
    initial_balance: Optional[float] = 0.0

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

class AgentResponse(AgentBase):
    id: str
    owner_id: str
    status: str
    wallet_address: Optional[str]
    performance_metrics: Dict[str, Any]
    created_at: datetime
    last_active: Optional[datetime]

    class Config:
        orm_mode = True

class TransactionBase(BaseModel):
    amount: Decimal
    transaction_type: str
    details: Optional[Dict[str, Any]] = None

class TransactionCreate(TransactionBase):
    agent_id: Optional[str] = None
    wallet_id: str

class TransactionResponse(TransactionBase):
    id: str
    user_id: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    error: Optional[str]

    class Config:
        orm_mode = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ServiceUsageCreate(BaseModel):
    agent_id: str
    service_type: str
    tokens_used: int
    cost: Decimal
    response_time: float
    metadata: Optional[Dict[str, Any]] = None

class ServiceUsageResponse(ServiceUsageCreate):
    id: int
    created_at: datetime
    success: bool
    error: Optional[str]

    class Config:
        orm_mode = True

class APIKeyCreate(BaseModel):
    name: str
    permissions: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None

class APIKeyResponse(BaseModel):
    id: str
    name: str
    key: str  # Only shown once upon creation
    permissions: Dict[str, Any]
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool

    class Config:
        orm_mode = True
