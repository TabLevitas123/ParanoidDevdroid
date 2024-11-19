# tokens/token_manager.py

from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
import asyncio
from datetime import datetime
import uuid

from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount

from config.constants import TokenType
from utils.logger import CustomLogger
from utils.error_handler import CustomException, handle_exceptions
from utils.smart_contract_utils import SmartContractManager
from utils.validation_utils import Validator

logger = CustomLogger("token_manager", "tokens.log")

class TokenManager:
    def __init__(self, smart_contract_manager: SmartContractManager):
        self.smart_contract_manager = smart_contract_manager
        self.validator = Validator()
        
        # Token contract addresses
        self.token_contracts: Dict[TokenType, str] = {}
        
        # Cache for token balances and allowances
        self.balance_cache: Dict[str, Dict[TokenType, Decimal]] = {}
        self.allowance_cache: Dict[str, Dict[str, Decimal]] = {}
        
        # Transaction history
        self.transaction_history: List[Dict[str, Any]] = []
        
        # Lock for atomic operations
        self.transfer_lock = asyncio.Lock()
        
        # Performance metrics
        self.performance_metrics = {
            'total_transactions': 0,
            'successful_transactions': 0,
            'failed_transactions': 0,
            'average_confirmation_time': 0.0,
            'total_volume': {
                TokenType.MAIN: Decimal('0'),
                TokenType.UTILITY: Decimal('0'),
                TokenType.GOVERNANCE: Decimal('0')
            }
        }

    @handle_exceptions
    async def initialize_token_contracts(
        self,
        main_token_address: str,
        utility_token_address: str,
        governance_token_address: str
    ) -> bool:
        """Initialize token contract addresses"""
        if not all(map(self.validator.validate_ethereum_address, 
                      [main_token_address, utility_token_address, governance_token_address])):
            raise CustomException(
                "TOKEN_003",
                "Invalid contract address format"
            )
            
        self.token_contracts = {
            TokenType.MAIN: main_token_address,
            TokenType.UTILITY: utility_token_address,
            TokenType.GOVERNANCE: governance_token_address
        }
        
        logger.info("Token contracts initialized")
        return True

    @handle_exceptions
    async def create_wallet(self) -> Dict[str, str]:
        """Create a new wallet for a user"""
        account: LocalAccount = self.smart_contract_manager.create_account()
        
        return {
            'address': account.address,
            'private_key': account.key.hex()  # This should be encrypted before storage
        }

    @handle_exceptions
    async def get_balance(
        self,
        address: str,
        token_type: Optional[TokenType] = None
    ) -> Union[Decimal, Dict[TokenType, Decimal]]:
        """Get token balance for an address"""
        if not self.validator.validate_ethereum_address(address):
            raise CustomException(
                "TOKEN_004",
                "Invalid wallet address",
                {"address": address}
            )
            
        try:
            if token_type:
                contract_address = self.token_contracts[token_type]
                balance = await self._get_token_balance(address, contract_address)
                self.balance_cache[address] = {
                    token_type: Decimal(str(balance))
                }
                return balance
            
            # Get balances for all token types
            balances = {}
            for token_type, contract_address in self.token_contracts.items():
                balance = await self._get_token_balance(address, contract_address)
                balances[token_type] = Decimal(str(balance))
            
            self.balance_cache[address] = balances
            return balances
            
        except Exception as e:
            logger.error(f"Failed to get balance: {str(e)}")
            raise CustomException(
                "TOKEN_005",
                "Failed to fetch balance",
                {"error": str(e)}
            )

    async def _get_token_balance(
        self,
        address: str,
        contract_address: str
    ) -> Decimal:
        """Get balance from smart contract"""
        try:
            result = await self.smart_contract_manager.send_transaction(
                "balanceOf",
                (address,),
                None,  # No private key needed for view functions
                0  # No gas needed for view functions
            )
            
            if not result['success']:
                raise CustomException(
                    "TOKEN_006",
                    "Balance check failed",
                    {"error": result.get('error')}
                )
                
            return Decimal(str(result['data']))
            
        except Exception as e:
            logger.error(f"Smart contract balance check failed: {str(e)}")
            raise

    @handle_exceptions
    async def transfer(
        self,
        from_address: str,
        to_address: str,
        amount: Union[int, float, Decimal],
        token_type: TokenType = TokenType.UTILITY,
        private_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transfer tokens between addresses"""
        # Input validation
        if not all(map(self.validator.validate_ethereum_address, [from_address, to_address])):
            raise CustomException(
                "TOKEN_004",
                "Invalid wallet address"
            )
            
        if not self.validator.validate_token_amount(float(amount)):
            raise CustomException(
                "TOKEN_007",
                "Invalid transfer amount",
                {"amount": amount}
            )
            
        # Convert amount to Decimal for precise calculations
        amount = Decimal(str(amount))
        
        # Check if sender has sufficient balance
        sender_balance = await self.get_balance(from_address, token_type)
        if sender_balance < amount:
            raise CustomException(
                "TOKEN_001",
                "Insufficient balance",
                {
                    "required": float(amount),
                    "available": float(sender_balance)
                }
            )
            
        # Create transaction record
        transaction_id = str(uuid.uuid4())
        transaction_record = {
            'transaction_id': transaction_id,
            'from_address': from_address,
            'to_address': to_address,
            'amount': amount,
            'token_type': token_type,
            'status': 'pending',
            'timestamp': datetime.utcnow().timestamp(),
            'gas_used': None,
            'block_number': None
        }
        
        # Acquire lock for atomic operation
        async with self.transfer_lock:
            try:
                # Send transaction to smart contract
                contract_address = self.token_contracts[token_type]
                start_time = datetime.utcnow().timestamp()
                
                result = await self.smart_contract_manager.send_transaction(
                    "transfer",
                    (to_address, int(amount * 10**18)),  # Convert to wei
                    private_key
                )
                
                if not result['success']:
                    raise CustomException(
                        "TOKEN_008",
                        "Transfer failed",
                        {"error": result.get('error')}
                    )
                
                # Update transaction record
                end_time = datetime.utcnow().timestamp()
                transaction_record.update({
                    'status': 'completed',
                    'gas_used': result['receipt']['gasUsed'],
                    'block_number': result['receipt']['blockNumber'],
                    'confirmation_time': end_time - start_time
                })
                
                # Update metrics
                self._update_metrics(transaction_record)
                
                # Invalidate balance cache
                self.balance_cache.pop(from_address, None)
                self.balance_cache.pop(to_address, None)
                
                logger.info(
                    f"Transfer completed: {amount} {token_type.value} "
                    f"from {from_address} to {to_address}"
                )
                
                return {
                    'success': True,
                    'transaction_id': transaction_id,
                    'block_number': transaction_record['block_number'],
                    'gas_used': transaction_record['gas_used']
                }
                
            except Exception as e:
                transaction_record['status'] = 'failed'
                transaction_record['error'] = str(e)
                logger.error(f"Transfer failed: {str(e)}")
                raise CustomException(
                    "TOKEN_008",
                    "Transfer failed",
                    {"error": str(e)}
                )
            
            finally:
                self.transaction_history.append(transaction_record)

    def _update_metrics(self, transaction_record: Dict[str, Any]) -> None:
        """Update performance metrics"""
        self.performance_metrics['total_transactions'] += 1
        
        if transaction_record['status'] == 'completed':
            self.performance_metrics['successful_transactions'] += 1
            token_type = transaction_record['token_type']
            self.performance_metrics['total_volume'][token_type] += transaction_record['amount']
            
            # Update average confirmation time
            current_avg = self.performance_metrics['average_confirmation_time']
            total_successful = self.performance_metrics['successful_transactions']
            new_time = transaction_record['confirmation_time']
            
            self.performance_metrics['average_confirmation_time'] = (
                (current_avg * (total_successful - 1) + new_time) / total_successful
            )
        else:
            self.performance_metrics['failed_transactions'] += 1

    @handle_exceptions
    async def check_allowance(
        self,
        owner_address: str,
        spender_address: str,
        token_type: TokenType = TokenType.UTILITY
    ) -> Decimal:
        """Check token allowance for a spender"""
        if not all(map(self.validator.validate_ethereum_address, [owner_address, spender_address])):
            raise CustomException(
                "TOKEN_004",
                "Invalid wallet address"
            )
            
        try:
            contract_address = self.token_contracts[token_type]
            result = await self.smart_contract_manager.send_transaction(
                "allowance",
                (owner_address, spender_address),
                None
            )
            
            if not result['success']:
                raise CustomException(
                    "TOKEN_009",
                    "Allowance check failed",
                    {"error": result.get('error')}
                )
                
            allowance = Decimal(str(result['data']))
            self.allowance_cache[f"{owner_address}:{spender_address}"] = allowance
            
            return allowance
            
        except Exception as e:
            logger.error(f"Failed to check allowance: {str(e)}")
            raise CustomException(
                "TOKEN_009",
                "Allowance check failed",
                {"error": str(e)}
            )

    @handle_exceptions
    async def approve_spender(
        self,
        owner_address: str,
        spender_address: str,
        amount: Union[int, float, Decimal],
        token_type: TokenType = TokenType.UTILITY,
        private_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Approve token allowance for a spender"""
        if not all(map(self.validator.validate_ethereum_address, [owner_address, spender_address])):
            raise CustomException(
                "TOKEN_004",
                "Invalid wallet address"
            )
            
        amount = Decimal(str(amount))
        if not self.validator.validate_token_amount(float(amount)):
            raise CustomException(
                "TOKEN_007",
                "Invalid approval amount",
                {"amount": amount}
            )
            
        try:
            contract_address = self.token_contracts[token_type]
            result = await self.smart_contract_manager.send_transaction(
                "approve",
                (spender_address, int(amount * 10**18)),
                private_key
            )
            
            if not result['success']:
                raise CustomException(
                    "TOKEN_010",
                    "Approval failed",
                    {"error": result.get('error')}
                )
                
            # Invalidate allowance cache
            self.allowance_cache.pop(f"{owner_address}:{spender_address}", None)
            
            return {
                'success': True,
                'transaction_hash': result['transaction_hash'],
                'owner': owner_address,
                'spender': spender_address,
                'amount': amount
            }
            
        except Exception as e:
            logger.error(f"Approval failed: {str(e)}")
            raise CustomException(
                "TOKEN_010",
                "Approval failed",
                {"error": str(e)}
            )

    @handle_exceptions
    async def get_transaction_history(
        self,
        address: Optional[str] = None,
        token_type: Optional[TokenType] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get transaction history with optional filters"""
        filtered_history = self.transaction_history
        
        if address:
            filtered_history = [
                tx for tx in filtered_history
                if tx['from_address'] == address or tx['to_address'] == address
            ]
            
        if token_type:
            filtered_history = [
                tx for tx in filtered_history
                if tx['token_type'] == token_type
            ]
            
        if status:
            filtered_history = [
                tx for tx in filtered_history
                if tx['status'] == status
            ]
            
        return filtered_history[offset:offset + limit]

    @handle_exceptions
    async def get_metrics(self) -> Dict[str, Any]:
        """Get token manager performance metrics"""
        return {
            'transactions': {
                'total': self.performance_metrics['total_transactions'],
                'successful': self.performance_metrics['successful_transactions'],
                'failed': self.performance_metrics['failed_transactions'],
                'success_rate': (
                    self.performance_metrics['successful_transactions'] /
                    self.performance_metrics['total_transactions']
                    if self.performance_metrics['total_transactions'] > 0 else 0
                )
            },
            'volume': {
                token_type.value: float(volume)
                for token_type, volume in self.performance_metrics['total_volume'].items()
            },
            'average_confirmation_time': self.performance_metrics['average_confirmation_time']
        }

    def __str__(self) -> str:
        return (f"TokenManager(transactions={self.performance_metrics['total_transactions']}, "
                f"success_rate={self.performance_metrics['successful_transactions']/self.performance_metrics['total_transactions']:.2%})")

    def __repr__(self) -> str:
        return (f"TokenManager(contracts={list(self.token_contracts.keys())}, "
                f"metrics={self.performance_metrics})")
