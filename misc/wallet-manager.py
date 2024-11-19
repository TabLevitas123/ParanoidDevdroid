# users/wallet_manager.py

from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
from datetime import datetime
import asyncio
import uuid

from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount

from config.constants import TokenType
from utils.logger import CustomLogger
from utils.error_handler import CustomException, handle_exceptions
from utils.validation_utils import Validator
from utils.encryption_manager import EncryptionManager
from tokens.token_manager import TokenManager

logger = CustomLogger("wallet_manager", "wallets.log")

class WalletEncryption:
    """Handles secure storage and encryption of wallet keys"""
    def __init__(self, encryption_manager: EncryptionManager):
        self.encryption_manager = encryption_manager
        self.key_store: Dict[str, bytes] = {}

    async def encrypt_private_key(self, private_key: str) -> bytes:
        """Encrypt a private key"""
        return self.encryption_manager.encrypt(private_key)

    async def decrypt_private_key(self, encrypted_key: bytes) -> str:
        """Decrypt a private key"""
        return self.encryption_manager.decrypt(encrypted_key).decode()

    async def store_private_key(self, wallet_address: str, private_key: str) -> bool:
        """Securely store an encrypted private key"""
        try:
            encrypted_key = await self.encrypt_private_key(private_key)
            self.key_store[wallet_address] = encrypted_key
            return True
        except Exception as e:
            logger.error(f"Failed to store private key: {str(e)}")
            return False

    async def get_private_key(self, wallet_address: str) -> Optional[str]:
        """Retrieve and decrypt a stored private key"""
        encrypted_key = self.key_store.get(wallet_address)
        if not encrypted_key:
            return None
        return await self.decrypt_private_key(encrypted_key)

class TransactionBuilder:
    """Handles construction and signing of blockchain transactions"""
    def __init__(self, web3_provider: str):
        self.w3 = Web3(Web3.HTTPProvider(web3_provider))

    async def build_transaction(
        self,
        from_address: str,
        to_address: str,
        value: Union[int, float, Decimal],
        gas_price: Optional[int] = None,
        gas_limit: int = 21000,
        data: str = ''
    ) -> Dict[str, Any]:
        """Build a transaction object"""
        try:
            nonce = self.w3.eth.get_transaction_count(from_address)
            gas_price = gas_price or self.w3.eth.gas_price
            
            transaction = {
                'nonce': nonce,
                'to': to_address,
                'value': self.w3.to_wei(value, 'ether'),
                'gas': gas_limit,
                'gasPrice': gas_price,
                'data': data,
                'chainId': self.w3.eth.chain_id
            }
            
            return transaction
            
        except Exception as e:
            logger.error(f"Failed to build transaction: {str(e)}")
            raise CustomException(
                "WALLET_001",
                "Transaction build failed",
                {"error": str(e)}
            )

    async def sign_transaction(
        self,
        transaction: Dict[str, Any],
        private_key: str
    ) -> str:
        """Sign a transaction with a private key"""
        try:
            signed_txn = self.w3.eth.account.sign_transaction(
                transaction,
                private_key
            )
            return signed_txn.rawTransaction.hex()
            
        except Exception as e:
            logger.error(f"Failed to sign transaction: {str(e)}")
            raise CustomException(
                "WALLET_002",
                "Transaction signing failed",
                {"error": str(e)}
            )

class WalletManager:
    """Main wallet management system"""
    def __init__(
        self,
        token_manager: TokenManager,
        encryption_manager: EncryptionManager,
        web3_provider: str
    ):
        self.token_manager = token_manager
        self.encryption = WalletEncryption(encryption_manager)
        self.transaction_builder = TransactionBuilder(web3_provider)
        self.validator = Validator()
        
        # Wallet data storage
        self.wallets: Dict[str, Dict[str, Any]] = {}
        self.user_wallets: Dict[str, List[str]] = {}
        
        # Transaction tracking
        self.pending_transactions: Dict[str, Dict[str, Any]] = {}
        self.transaction_history: List[Dict[str, Any]] = {}
        
        # Performance metrics
        self.metrics = {
            'total_wallets': 0,
            'active_wallets': 0,
            'total_transactions': 0,
            'successful_transactions': 0,
            'failed_transactions': 0,
            'average_gas_price': Decimal('0'),
            'total_gas_spent': Decimal('0')
        }

    @handle_exceptions
    async def create_wallet(
        self,
        user_id: str,
        wallet_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new wallet for a user"""
        try:
            # Generate new account
            account: LocalAccount = Account.create()
            wallet_id = str(uuid.uuid4())
            
            # Store wallet data
            wallet_data = {
                'wallet_id': wallet_id,
                'address': account.address,
                'name': wallet_name or f"Wallet {len(self.user_wallets.get(user_id, [])) + 1}",
                'user_id': user_id,
                'created_at': datetime.utcnow().timestamp(),
                'last_active': datetime.utcnow().timestamp(),
                'is_active': True
            }
            
            # Store encrypted private key
            await self.encryption.store_private_key(
                account.address,
                account.key.hex()
            )
            
            # Update storage
            self.wallets[wallet_id] = wallet_data
            if user_id not in self.user_wallets:
                self.user_wallets[user_id] = []
            self.user_wallets[user_id].append(wallet_id)
            
            # Update metrics
            self.metrics['total_wallets'] += 1
            self.metrics['active_wallets'] += 1
            
            return {
                'wallet_id': wallet_id,
                'address': account.address,
                'name': wallet_data['name']
            }
            
        except Exception as e:
            logger.error(f"Wallet creation failed: {str(e)}")
            raise CustomException(
                "WALLET_003",
                "Wallet creation failed",
                {"error": str(e)}
            )

    @handle_exceptions
    async def get_wallet(
        self,
        wallet_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Get wallet information"""
        if wallet_id not in self.wallets:
            raise CustomException(
                "WALLET_004",
                "Wallet not found"
            )
            
        wallet = self.wallets[wallet_id]
        if wallet['user_id'] != user_id:
            raise CustomException(
                "WALLET_005",
                "Unauthorized wallet access"
            )
            
        return {
            'wallet_id': wallet['wallet_id'],
            'address': wallet['address'],
            'name': wallet['name'],
            'created_at': wallet['created_at'],
            'last_active': wallet['last_active'],
            'is_active': wallet['is_active']
        }

    @handle_exceptions
    async def list_user_wallets(self, user_id: str) -> List[Dict[str, Any]]:
        """List all wallets owned by a user"""
        wallet_ids = self.user_wallets.get(user_id, [])
        return [
            await self.get_wallet(wallet_id, user_id)
            for wallet_id in wallet_ids
        ]

    @handle_exceptions
    async def send_transaction(
        self,
        wallet_id: str,
        user_id: str,
        to_address: str,
        amount: Union[int, float, Decimal],
        token_type: TokenType = TokenType.UTILITY,
        gas_price: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send a transaction from a wallet"""
        # Validate wallet ownership
        wallet = await self.get_wallet(wallet_id, user_id)
        
        # Validate addresses
        if not self.validator.validate_ethereum_address(to_address):
            raise CustomException(
                "WALLET_006",
                "Invalid recipient address"
            )
            
        # Check balance
        balance = await self.token_manager.get_balance(
            wallet['address'],
            token_type
        )
        
        if balance < Decimal(str(amount)):
            raise CustomException(
                "WALLET_007",
                "Insufficient balance",
                {
                    "required": float(amount),
                    "available": float(balance)
                }
            )
            
        try:
            # Get private key
            private_key = await self.encryption.get_private_key(wallet['address'])
            if not private_key:
                raise CustomException(
                    "WALLET_008",
                    "Private key not found"
                )
                
            # Build transaction
            transaction = await self.transaction_builder.build_transaction(
                wallet['address'],
                to_address,
                amount,
                gas_price
            )
            
            # Sign transaction
            signed_tx = await self.transaction_builder.sign_transaction(
                transaction,
                private_key
            )
            
            # Send transaction through token manager
            result = await self.token_manager.transfer(
                wallet['address'],
                to_address,
                amount,
                token_type,
                signed_tx
            )
            
            # Update wallet status
            self.wallets[wallet_id]['last_active'] = datetime.utcnow().timestamp()
            
            # Update metrics
            self.metrics['total_transactions'] += 1
            if result['success']:
                self.metrics['successful_transactions'] += 1
                self.metrics['total_gas_spent'] += Decimal(str(result['gas_used']))
                self.metrics['average_gas_price'] = (
                    (self.metrics['average_gas_price'] * (self.metrics['successful_transactions'] - 1) +
                     Decimal(str(transaction['gasPrice']))) /
                    self.metrics['successful_transactions']
                )
            else:
                self.metrics['failed_transactions'] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Transaction failed: {str(e)}")
            raise CustomException(
                "WALLET_009",
                "Transaction failed",
                {"error": str(e)}
            )

    @handle_exceptions
    async def get_transaction_history(
        self,
        wallet_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get transaction history for a wallet"""
        wallet = await self.get_wallet(wallet_id, user_id)
        
        # Filter transactions for this wallet
        wallet_transactions = [
            tx for tx in self.transaction_history
            if tx['from_address'] == wallet['address'] or
               tx['to_address'] == wallet['address']
        ]
        
        return wallet_transactions[offset:offset + limit]

    @handle_exceptions
    async def get_metrics(self) -> Dict[str, Any]:
        """Get wallet management metrics"""
        return {
            'wallets': {
                'total': self.metrics['total_wallets'],
                'active': self.metrics['active_wallets']
            },
            'transactions': {
                'total': self.metrics['total_transactions'],
                'successful': self.metrics['successful_transactions'],
                'failed': self.metrics['failed_transactions'],
                'success_rate': (
                    self.metrics['successful_transactions'] /
                    self.metrics['total_transactions']
                    if self.metrics['total_transactions'] > 0
                    else 0
                )
            },
            'gas': {
                'average_price': float(self.metrics['average_gas_price']),
                'total_spent': float(self.metrics['total_gas_spent'])
            }
        }

    def __str__(self) -> str:
        return f"WalletManager(wallets={self.metrics['total_wallets']})"

    def __repr__(self) -> str:
        return (f"WalletManager(total_wallets={self.metrics['total_wallets']}, "
                f"active_wallets={self.metrics['active_wallets']})")
