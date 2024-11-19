# users/user_manager.py

from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import asyncio
from dataclasses import dataclass
import jwt
from passlib.hash import argon2

from utils.logger import CustomLogger
from utils.error_handler import CustomException, handle_exceptions
from utils.validation_utils import Validator
from utils.encryption_manager import EncryptionManager
from tokens.token_manager import TokenManager

logger = CustomLogger("user_manager", "users.log")

@dataclass
class UserProfile:
    user_id: str
    username: str
    email: str
    created_at: float
    last_active: float
    is_active: bool
    roles: List[str]
    preferences: Dict[str, Any]

class UserAuthenticator:
    """Handles user authentication and session management"""
    def __init__(self, encryption_manager: EncryptionManager, jwt_secret: str):
        self.encryption_manager = encryption_manager
        self.jwt_secret = jwt_secret
        self.password_hasher = argon2
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    async def create_password_hash(self, password: str) -> str:
        return self.password_hasher.hash(password)

    async def verify_password(self, password: str, password_hash: str) -> bool:
        return self.password_hasher.verify(password, password_hash)

    async def create_session(self, user_id: str, device_info: Dict[str, str]) -> Dict[str, str]:
        session_id = str(uuid.uuid4())
        token = jwt.encode(
            {
                'user_id': user_id,
                'session_id': session_id,
                'exp': datetime.utcnow().timestamp() + 3600  # 1 hour expiration
            },
            self.jwt_secret,
            algorithm='HS256'
        )
        
        self.active_sessions[session_id] = {
            'user_id': user_id,
            'device_info': device_info,
            'created_at': datetime.utcnow().timestamp(),
            'last_active': datetime.utcnow().timestamp()
        }
        
        return {
            'session_id': session_id,
            'token': token
        }

    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            session = self.active_sessions.get(payload['session_id'])
            
            if not session or session['user_id'] != payload['user_id']:
                return None
                
            return payload
        except jwt.InvalidTokenError:
            return None

class UserStorage:
    """Handles user data storage and retrieval"""
    def __init__(self, encryption_manager: EncryptionManager):
        self.encryption_manager = encryption_manager
        self.users: Dict[str, Dict[str, Any]] = {}
        self.email_index: Dict[str, str] = {}
        self.username_index: Dict[str, str] = {}

    async def store_user(self, user_data: Dict[str, Any]) -> bool:
        user_id = user_data['user_id']
        self.users[user_id] = user_data
        self.email_index[user_data['email']] = user_id
        self.username_index[user_data['username']] = user_id
        return True

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.users.get(user_id)

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        user_id = self.email_index.get(email)
        return self.users.get(user_id) if user_id else None

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        user_id = self.username_index.get(username)
        return self.users.get(user_id) if user_id else None

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        if user_id not in self.users:
            return False
            
        current_data = self.users[user_id]
        
        # Update indices if necessary
        if 'email' in updates and updates['email'] != current_data['email']:
            del self.email_index[current_data['email']]
            self.email_index[updates['email']] = user_id
            
        if 'username' in updates and updates['username'] != current_data['username']:
            del self.username_index[current_data['username']]
            self.username_index[updates['username']] = user_id
        
        current_data.update(updates)
        return True

class UserManager:
    """Main user management system"""
    def __init__(
        self,
        token_manager: TokenManager,
        encryption_manager: EncryptionManager,
        jwt_secret: str
    ):
        self.token_manager = token_manager
        self.authenticator = UserAuthenticator(encryption_manager, jwt_secret)
        self.storage = UserStorage(encryption_manager)
        self.validator = Validator()
        
        # Rate limiting
        self.login_attempts: Dict[str, List[float]] = {}
        self.max_attempts = 5
        self.attempt_window = 300  # 5 minutes
        
        # Performance metrics
        self.metrics = {
            'total_users': 0,
            'active_users': 0,
            'failed_logins': 0,
            'successful_logins': 0
        }

    @handle_exceptions
    async def register_user(
        self,
        username: str,
        email: str,
        password: str,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Register a new user"""
        # Validate inputs
        if not self.validator.validate_email(email):
            raise CustomException(
                "USER_001",
                "Invalid email format",
                {"email": email}
            )
            
        password_validation = self.validator.validate_password(password)
        if not password_validation['valid']:
            raise CustomException(
                "USER_002",
                "Invalid password",
                {"issues": password_validation['issues']}
            )
            
        # Check for existing user
        if await self.storage.get_user_by_email(email):
            raise CustomException(
                "USER_003",
                "Email already registered"
            )
            
        if await self.storage.get_user_by_username(username):
            raise CustomException(
                "USER_004",
                "Username already taken"
            )
            
        try:
            # Create user profile
            user_id = str(uuid.uuid4())
            current_time = datetime.utcnow().timestamp()
            
            user_data = {
                'user_id': user_id,
                'username': username,
                'email': email,
                'password_hash': await self.authenticator.create_password_hash(password),
                'created_at': current_time,
                'last_active': current_time,
                'is_active': True,
                'roles': ['user'],
                'preferences': additional_info or {},
                'wallet_address': None
            }
            
            # Create wallet
            wallet = await self.token_manager.create_wallet()
            user_data['wallet_address'] = wallet['address']
            
            # Store user data
            await self.storage.store_user(user_data)
            
            # Update metrics
            self.metrics['total_users'] += 1
            self.metrics['active_users'] += 1
            
            return UserProfile(
                user_id=user_id,
                username=username,
                email=email,
                created_at=current_time,
                last_active=current_time,
                is_active=True,
                roles=['user'],
                preferences=additional_info or {}
            )
            
        except Exception as e:
            logger.error(f"User registration failed: {str(e)}")
            raise CustomException(
                "USER_005",
                "Registration failed",
                {"error": str(e)}
            )

    @handle_exceptions
    async def login(
        self,
        email: str,
        password: str,
        device_info: Dict[str, str]
    ) -> Dict[str, Any]:
        """Authenticate user and create session"""
        # Check rate limiting
        if not await self._check_rate_limit(email):
            raise CustomException(
                "USER_006",
                "Too many login attempts",
                {"retry_after": self.attempt_window}
            )
            
        try:
            # Get user data
            user_data = await self.storage.get_user_by_email(email)
            if not user_data:
                self.metrics['failed_logins'] += 1
                await self._record_login_attempt(email)
                raise CustomException("USER_007", "Invalid credentials")
                
            # Verify password
            if not await self.authenticator.verify_password(
                password,
                user_data['password_hash']
            ):
                self.metrics['failed_logins'] += 1
                await self._record_login_attempt(email)
                raise CustomException("USER_007", "Invalid credentials")
                
            # Create session
            session = await self.authenticator.create_session(
                user_data['user_id'],
                device_info
            )
            
            # Update user status
            await self.storage.update_user(
                user_data['user_id'],
                {'last_active': datetime.utcnow().timestamp()}
            )
            
            self.metrics['successful_logins'] += 1
            
            return {
                'user': UserProfile(
                    user_id=user_data['user_id'],
                    username=user_data['username'],
                    email=user_data['email'],
                    created_at=user_data['created_at'],
                    last_active=user_data['last_active'],
                    is_active=user_data['is_active'],
                    roles=user_data['roles'],
                    preferences=user_data['preferences']
                ),
                'session': session
            }
            
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            raise CustomException(
                "USER_008",
                "Login failed",
                {"error": str(e)}
            )

    async def _check_rate_limit(self, email: str) -> bool:
        """Check if login attempts are within rate limit"""
        if email not in self.login_attempts:
            return True
            
        current_time = datetime.utcnow().timestamp()
        recent_attempts = [
            attempt for attempt in self.login_attempts[email]
            if current_time - attempt < self.attempt_window
        ]
        
        self.login_attempts[email] = recent_attempts
        return len(recent_attempts) < self.max_attempts

    async def _record_login_attempt(self, email: str) -> None:
        """Record a failed login attempt"""
        current_time = datetime.utcnow().timestamp()
        if email not in self.login_attempts:
            self.login_attempts[email] = []
        self.login_attempts[email].append(current_time)

    @handle_exceptions
    async def get_user_profile(
        self,
        user_id: str,
        token: Optional[str] = None
    ) -> UserProfile:
        """Get user profile information"""
        if token:
            payload = await self.authenticator.validate_token(token)
            if not payload or payload['user_id'] != user_id:
                raise CustomException(
                    "USER_009",
                    "Unauthorized access"
                )
                
        user_data = await self.storage.get_user(user_id)
        if not user_data:
            raise CustomException(
                "USER_010",
                "User not found"
            )
            
        return UserProfile(
            user_id=user_data['user_id'],
            username=user_data['username'],
            email=user_data['email'],
            created_at=user_data['created_at'],
            last_active=user_data['last_active'],
            is_active=user_data['is_active'],
            roles=user_data['roles'],
            preferences=user_data['preferences']
        )

    @handle_exceptions
    async def update_user_profile(
        self,
        user_id: str,
        updates: Dict[str, Any],
        token: str
    ) -> UserProfile:
        """Update user profile information"""
        # Validate token
        payload = await self.authenticator.validate_token(token)
        if not payload or payload['user_id'] != user_id:
            raise CustomException(
                "USER_009",
                "Unauthorized access"
            )
            
        # Get current user data
        user_data = await self.storage.get_user(user_id)
        if not user_data:
            raise CustomException(
                "USER_010",
                "User not found"
            )
            
        # Validate updates
        if 'email' in updates and not self.validator.validate_email(updates['email']):
            raise CustomException(
                "USER_001",
                "Invalid email format",
                {"email": updates['email']}
            )
            
        # Apply updates
        success = await self.storage.update_user(user_id, updates)
        if not success:
            raise CustomException(
                "USER_011",
                "Profile update failed"
            )
            
        # Get updated profile
        return await self.get_user_profile(user_id)

    @handle_exceptions
    async def get_metrics(self) -> Dict[str, Any]:
        """Get user management metrics"""
        return {
            'users': {
                'total': self.metrics['total_users'],
                'active': self.metrics['active_users']
            },
            'logins': {
                'successful': self.metrics['successful_logins'],
                'failed': self.metrics['failed_logins'],
                'success_rate': (
                    self.metrics['successful_logins'] /
                    (self.metrics['successful_logins'] + self.metrics['failed_logins'])
                    if (self.metrics['successful_logins'] + self.metrics['failed_logins']) > 0
                    else 0
                )
            }
        }

    def __str__(self) -> str:
        return f"UserManager(users={self.metrics['total_users']})"

    def __repr__(self) -> str:
        return (f"UserManager(total_users={self.metrics['total_users']}, "
                f"active_users={self.metrics['active_users']})")
