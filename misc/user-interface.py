# users/user_interface.py

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import asyncio
from decimal import Decimal

from flask import Flask, request, jsonify, Response
from pydantic import BaseModel, Field, validator
import jwt

from utils.logger import CustomLogger
from utils.error_handler import CustomException, handle_exceptions
from utils.validation_utils import Validator, BaseRequest
from users.user_manager import UserManager
from users.wallet_manager import WalletManager
from tokens.token_manager import TokenManager
from config.constants import TokenType

logger = CustomLogger("user_interface", "api.log")

# Request/Response Models
class RegisterRequest(BaseRequest):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    password: str = Field(..., min_length=8)
    additional_info: Optional[Dict[str, Any]] = None

class LoginRequest(BaseRequest):
    email: str
    password: str
    device_info: Dict[str, str]

class UpdateProfileRequest(BaseRequest):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[str] = Field(None, regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    preferences: Optional[Dict[str, Any]] = None

class CreateWalletRequest(BaseRequest):
    wallet_name: Optional[str] = Field(None, min_length=1, max_length=50)

class TransactionRequest(BaseRequest):
    to_address: str = Field(..., regex=r'^0x[a-fA-F0-9]{40}$')
    amount: Union[int, float, Decimal]
    token_type: TokenType = TokenType.UTILITY
    gas_price: Optional[int] = None

class UserInterface:
    """API interface for user interactions"""
    def __init__(
        self,
        user_manager: UserManager,
        wallet_manager: WalletManager,
        token_manager: TokenManager
    ):
        self.user_manager = user_manager
        self.wallet_manager = wallet_manager
        self.token_manager = token_manager
        self.validator = Validator()
        
        # Initialize Flask app
        self.app = Flask(__name__)
        self.setup_routes()
        
        # Rate limiting
        self.rate_limits: Dict[str, List[float]] = {}
        self.rate_limit_window = 3600  # 1 hour
        self.rate_limit_max_requests = 1000

    def setup_routes(self):
        """Configure API routes"""
        # User management routes
        self.app.route('/api/users/register', methods=['POST'])(self.register_user)
        self.app.route('/api/users/login', methods=['POST'])(self.login)
        self.app.route('/api/users/profile', methods=['GET'])(self.get_profile)
        self.app.route('/api/users/profile', methods=['PUT'])(self.update_profile)
        
        # Wallet management routes
        self.app.route('/api/wallets', methods=['POST'])(self.create_wallet)
        self.app.route('/api/wallets', methods=['GET'])(self.list_wallets)
        self.app.route('/api/wallets/<wallet_id>', methods=['GET'])(self.get_wallet)
        self.app.route('/api/wallets/<wallet_id>/transactions', methods=['POST'])(self.send_transaction)
        self.app.route('/api/wallets/<wallet_id>/transactions', methods=['GET'])(self.get_transactions)
        
        # Token management routes
        self.app.route('/api/tokens/balance/<token_type>', methods=['GET'])(self.get_token_balance)
        
        # Error handlers
        self.app.errorhandler(CustomException)(self.handle_custom_error)
        self.app.errorhandler(Exception)(self.handle_error)

    async def _validate_token(self, required: bool = True) -> Optional[Dict[str, Any]]:
        """Validate authentication token from request"""
        auth_header = request.headers.get('Authorization')
        if not auth_header and required:
            raise CustomException(
                "AUTH_001",
                "Missing authentication token"
            )
            
        if not auth_header:
            return None
            
        try:
            token = auth_header.split(' ')[1]
            return await self.user_manager.authenticator.validate_token(token)
        except (IndexError, jwt.InvalidTokenError):
            if required:
                raise CustomException(
                    "AUTH_002",
                    "Invalid authentication token"
                )
            return None

    async def _check_rate_limit(self, endpoint: str, user_id: Optional[str] = None) -> bool:
        """Check if request is within rate limits"""
        key = f"{endpoint}:{user_id}" if user_id else endpoint
        current_time = datetime.utcnow().timestamp()
        
        if key not in self.rate_limits:
            self.rate_limits[key] = []
            
        # Clean old requests
        self.rate_limits[key] = [
            timestamp for timestamp in self.rate_limits[key]
            if current_time - timestamp < self.rate_limit_window
        ]
        
        # Check limit
        if len(self.rate_limits[key]) >= self.rate_limit_max_requests:
            return False
            
        self.rate_limits[key].append(current_time)
        return True

    @handle_exceptions
    async def register_user(self) -> Response:
        """Handle user registration"""
        try:
            data = RegisterRequest(**request.json)
            
            if not await self._check_rate_limit('register'):
                raise CustomException(
                    "RATE_001",
                    "Rate limit exceeded"
                )
                
            user = await self.user_manager.register_user(
                data.username,
                data.email,
                data.password,
                data.additional_info
            )
            
            return jsonify({
                'success': True,
                'user': user
            })
            
        except ValidationError as e:
            raise CustomException(
                "VAL_001",
                "Validation error",
                {'errors': e.errors()}
            )

    @handle_exceptions
    async def login(self) -> Response:
        """Handle user login"""
        try:
            data = LoginRequest(**request.json)
            
            if not await self._check_rate_limit('login'):
                raise CustomException(
                    "RATE_001",
                    "Rate limit exceeded"
                )
                
            result = await self.user_manager.login(
                data.email,
                data.password,
                data.device_info
            )
            
            return jsonify({
                'success': True,
                'user': result['user'],
                'token': result['session']['token']
            })
            
        except ValidationError as e:
            raise CustomException(
                "VAL_001",
                "Validation error",
                {'errors': e.errors()}
            )

    @handle_exceptions
    async def get_profile(self) -> Response:
        """Get user profile information"""
        token_data = await self._validate_token()
        
        if not await self._check_rate_limit('profile', token_data['user_id']):
            raise CustomException(
                "RATE_001",
                "Rate limit exceeded"
            )
            
        profile = await self.user_manager.get_user_profile(
            token_data['user_id'],
            request.headers['Authorization'].split(' ')[1]
        )
        
        return jsonify({
            'success': True,
            'profile': profile
        })

    @handle_exceptions
    async def update_profile(self) -> Response:
        """Update user profile information"""
        token_data = await self._validate_token()
        
        try:
            data = UpdateProfileRequest(**request.json)
            
            if not await self._check_rate_limit('profile_update', token_data['user_id']):
                raise CustomException(
                    "RATE_001",
                    "Rate limit exceeded"
                )
                
            profile = await self.user_manager.update_user_profile(
                token_data['user_id'],
                data.dict(exclude_unset=True),
                request.headers['Authorization'].split(' ')[1]
            )
            
            return jsonify({
                'success': True,
                'profile': profile
            })
            
        except ValidationError as e:
            raise CustomException(
                "VAL_001",
                "Validation error",
                {'errors': e.errors()}
            )

    @handle_exceptions
    async def create_wallet(self) -> Response:
        """Create new wallet for user"""
        token_data = await self._validate_token()
        
        try:
            data = CreateWalletRequest(**request.json)
            
            if not await self._check_rate_limit('wallet_create', token_data['user_id']):
                raise CustomException(
                    "RATE_001",
                    "Rate limit exceeded"
                )
                
            wallet = await self.wallet_manager.create_wallet(
                token_data['user_id'],
                data.wallet_name
            )
            
            return jsonify({
                'success': True,
                'wallet': wallet
            })
            
        except ValidationError as e:
            raise CustomException(
                "VAL_001",
                "Validation error",
                {'errors': e.errors()}
            )

    @handle_exceptions
    async def list_wallets(self) -> Response:
        """List user's wallets"""
        token_data = await self._validate_token()
        
        if not await self._check_rate_limit('wallet_list', token_data['user_id']):
            raise CustomException(
                "RATE_001",
                "Rate limit exceeded"
            )
            
        wallets = await self.wallet_manager.list_user_wallets(token_data['user_id'])
        
        return jsonify({
            'success': True,
            'wallets': wallets
        })

    @handle_exceptions
    async def get_wallet(self, wallet_id: str) -> Response:
        """Get specific wallet information"""
        token_data = await self._validate_token()
        
        if not await self._check_rate_limit('wallet_info', token_data['user_id']):
            raise CustomException(
                "RATE_001",
                "Rate limit exceeded"
            )
            
        wallet = await self.wallet_manager.get_wallet(
            wallet_id,
            token_data['user_id']
        )
        
        return jsonify({
            'success': True,
            'wallet': wallet
        })

    @handle_exceptions
    async def send_transaction(self, wallet_id: str) -> Response:
        """Send transaction from wallet"""
        token_data = await self._validate_token()
        
        try:
            data = TransactionRequest(**request.json)
            
            if not await self._check_rate_limit('transaction', token_data['user_id']):
                raise CustomException(
                    "RATE_001",
                    "Rate limit exceeded"
                )
                
            result = await self.wallet_manager.send_transaction(
                wallet_id,
                token_data['user_id'],
                data.to_address,
                data.amount,
                data.token_type,
                data.gas_price
            )
            
            return jsonify({
                'success': True,
                'transaction': result
            })
            
        except ValidationError as e:
            raise CustomException(
                "VAL_001",
                "Validation error",
                {'errors': e.errors()}
            )

    @handle_exceptions
    async def get_transactions(self, wallet_id: str) -> Response:
        """Get wallet transaction history"""
        token_data = await self._validate_token()
        
        if not await self._check_rate_limit('transaction_history', token_data['user_id']):
            raise CustomException(
                "RATE_001",
                "Rate limit exceeded"
            )
            
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        transactions = await self.wallet_manager.get_transaction_history(
            wallet_id,
            token_data['user_id'],
            limit,
            offset
        )
        
        return jsonify({
            'success': True,
            'transactions': transactions
        })

    @handle_exceptions
    async def get_token_balance(self, token_type: str) -> Response:
        """Get token balance for user"""
        token_data = await self._validate_token()
        
        if not await self._check_rate_limit('balance', token_data['user_id']):
            raise CustomException(
                "RATE_001",
                "Rate limit exceeded"
            )
            
        try:
            token_enum = TokenType(token_type)
        except ValueError:
            raise CustomException(
                "VAL_002",
                "Invalid token type",
                {'valid_types': [t.value for t in TokenType]}
            )
            
        wallets = await self.wallet_manager.list_user_wallets(token_data['user_id'])
        balances = {}
        
        for wallet in wallets:
            balance = await self.token_manager.get_balance(
                wallet['address'],
                token_enum
            )
            balances[wallet['wallet_id']] = float(balance)
            
        return jsonify({
            'success': True,
            'balances': balances
        })

    def handle_custom_error(self, error: CustomException) -> Response:
        """Handle custom exceptions"""
        return jsonify({
            'success': False,
            'error': {
                'code': error.error_code,
                'message': error.message,
                'details': error.details
            }
        }), 400

    def handle_error(self, error: Exception) -> Response:
        """Handle unexpected exceptions"""
        logger.error(f"Unexpected error: {str(error)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An unexpected error occurred'
            }
        }), 500

    def run(self, host: str = '0.0.0.0', port: int = 5000):
        """Start the API server"""
        self.app.run(host=host, port=port)

    def __str__(self) -> str:
        return "UserInterface(API)"

    def __repr__(self) -> str:
        return "UserInterface(Flask API Server)"
