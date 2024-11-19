# utils/logger.py
import logging
import sys
from typing import Optional
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime

class CustomLogger:
    def __init__(self, name: str, log_file: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (if log_file specified)
        if log_file:
            os.makedirs('logs', exist_ok=True)
            file_handler = RotatingFileHandler(
                f'logs/{log_file}',
                maxBytes=10485760,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def debug(self, message: str):
        self.logger.debug(message)
    
    def info(self, message: str):
        self.logger.info(message)
    
    def warning(self, message: str):
        self.logger.warning(message)
    
    def error(self, message: str):
        self.logger.error(message)
    
    def critical(self, message: str):
        self.logger.critical(message)

# utils/error_handler.py
from typing import Dict, Any, Optional
from functools import wraps
import traceback
from .logger import CustomLogger
from config.constants import ERROR_CODES

logger = CustomLogger("error_handler", "errors.log")

class CustomException(Exception):
    def __init__(self, error_code: str, message: str, details: Optional[Dict] = None):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

def handle_exceptions(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except CustomException as e:
            logger.error(f"Custom error: {e.error_code} - {e.message}")
            return {
                "success": False,
                "error_code": e.error_code,
                "message": e.message,
                "details": e.details
            }
        except Exception as e:
            error_details = {
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
            logger.critical(f"Unexpected error: {str(e)}\n{error_details['traceback']}")
            return {
                "success": False,
                "error_code": "SYSTEM_ERROR",
                "message": "An unexpected error occurred",
                "details": error_details
            }
    return wrapper

# utils/encryption_manager.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import base64
import os
from typing import Union

class EncryptionManager:
    def __init__(self, key: Optional[bytes] = None):
        self.key = key or Fernet.generate_key()
        self.cipher_suite = Fernet(self.key)
        
    def generate_key(self) -> bytes:
        """Generate a new encryption key"""
        return Fernet.generate_key()
    
    def encrypt(self, data: Union[str, bytes]) -> bytes:
        """Encrypt data using Fernet symmetric encryption"""
        if isinstance(data, str):
            data = data.encode()
        return self.cipher_suite.encrypt(data)
    
    def decrypt(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using Fernet symmetric encryption"""
        return self.cipher_suite.decrypt(encrypted_data)
    
    def hash_password(self, password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
        """Hash password using PBKDF2"""
        salt = salt or os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.b64encode(kdf.derive(password.encode()))
        return key, salt

# utils/smart_contract_utils.py
from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount
from typing import Dict, Any, Optional
import json
from .logger import CustomLogger

logger = CustomLogger("smart_contract_utils", "blockchain.log")

class SmartContractManager:
    def __init__(self, web3_provider: str, contract_address: str, abi_path: str):
        self.w3 = Web3(Web3.HTTPProvider(web3_provider))
        self.contract_address = contract_address
        
        # Load contract ABI
        with open(abi_path, 'r') as f:
            contract_abi = json.load(f)
        
        self.contract = self.w3.eth.contract(
            address=self.contract_address,
            abi=contract_abi
        )
    
    def create_account(self) -> LocalAccount:
        """Create a new Ethereum account"""
        return Account.create()
    
    async def send_transaction(
        self,
        function_name: str,
        args: tuple,
        private_key: str,
        gas_price_gwei: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send a transaction to the smart contract"""
        try:
            account = Account.from_key(private_key)
            
            # Get the contract function
            contract_function = getattr(self.contract.functions, function_name)
            
            # Build the transaction
            transaction = contract_function(*args).build_transaction({
                'from': account.address,
                'nonce': self.w3.eth.get_transaction_count(account.address),
                'gas': 2000000,  # Adjust gas limit as needed
                'gasPrice': self.w3.eth.gas_price if not gas_price_gwei else Web3.to_wei(gas_price_gwei, 'gwei')
            })
            
            # Sign and send the transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for transaction receipt
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return {
                'success': True,
                'transaction_hash': tx_hash.hex(),
                'receipt': dict(tx_receipt)
            }
            
        except Exception as e:
            logger.error(f"Transaction failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

# utils/validation_utils.py
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, validator
import re
from datetime import datetime

class ValidationError(Exception):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")

class Validator:
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        """
        Validate password strength
        Returns dict with validation result and any issues found
        """
        issues = []
        if len(password) < 8:
            issues.append("Password must be at least 8 characters long")
        if not re.search(r'[A-Z]', password):
            issues.append("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', password):
            issues.append("Password must contain at least one lowercase letter")
        if not re.search(r'\d', password):
            issues.append("Password must contain at least one number")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            issues.append("Password must contain at least one special character")
            
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    @staticmethod
    def validate_ethereum_address(address: str) -> bool:
        """Validate Ethereum address format"""
        pattern = r'^0x[a-fA-F0-9]{40}$'
        return bool(re.match(pattern, address))
    
    @staticmethod
    def validate_token_amount(amount: float, min_amount: float = 0) -> bool:
        """Validate token amount"""
        return amount > min_amount and isinstance(amount, (int, float))
    
    @staticmethod
    def sanitize_input(input_str: str) -> str:
        """Sanitize input string to prevent injection attacks"""
        # Remove any HTML tags
        clean_text = re.sub(r'<[^>]*>', '', input_str)
        # Remove any script tags and their contents
        clean_text = re.sub(r'<script[\s\S]*?</script>', '', clean_text)
        # Remove any potentially harmful characters
        clean_text = re.sub(r'[;\'"\\]', '', clean_text)
        return clean_text.strip()

class BaseRequest(BaseModel):
    """Base class for request validation"""
    @validator('*', pre=True)
    def remove_whitespace(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v
    
    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        # Remove None values
        return {k: v for k, v in d.items() if v is not None}
