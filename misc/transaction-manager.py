# marketplace/transaction_manager.py

from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime
import uuid
import asyncio

from utils.logger import CustomLogger
from utils.error_handler import CustomException, handle_exceptions
from utils.validation_utils import Validator
from tokens.token_manager import TokenManager
from agents.agent_manager import AgentManager

logger = CustomLogger("transaction_manager", "marketplace.log")

class TransactionState:
    """Enumeration of transaction states"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    DISPUTED = "disputed"

class TransactionManager:
    """Manages marketplace transactions"""
    def __init__(
        self,
        token_manager: TokenManager,
        agent_manager: AgentManager,
        validator: Validator
    ):
        self.token_manager = token_manager
        self.agent_manager = agent_manager
        self.validator = validator
        
        # Transaction storage
        self.transactions: Dict[str, Dict[str, Any]] = {}
        self.user_transactions: Dict[str, List[str]] = {}  # user_id -> transaction_ids
        self.agent_transactions: Dict[str, List[str]] = {}  # agent_id -> transaction_ids
        
        # Active processing
        self.active_transactions: Dict[str, asyncio.Task] = {}
        
        # Transaction fee configuration
        self.fee_config = {
            'base_fee_rate': Decimal('0.025'),  # 2.5%
            'min_fee': Decimal('0.1'),
            'max_fee': Decimal('100.0'),
            'volume_discount_tiers': {
                Decimal('1000'): Decimal('0.02'),   # 2.0% for volume > 1000
                Decimal('10000'): Decimal('0.015'), # 1.5% for volume > 10000
                Decimal('100000'): Decimal('0.01')  # 1.0% for volume > 100000
            }
        }
        
        # Performance metrics
        self.metrics = {
            'total_transactions': 0,
            'successful_transactions': 0,
            'failed_transactions': 0,
            'total_volume': Decimal('0'),
            'total_fees': Decimal('0'),
            'average_completion_time': 0.0,
            'dispute_rate': 0.0
        }

    def _calculate_fee(
        self,
        amount: Decimal,
        user_volume: Decimal
    ) -> Decimal:
        """Calculate transaction fee based on amount and user volume"""
        # Determine applicable fee rate based on volume
        fee_rate = self.fee_config['base_fee_rate']
        for volume_threshold, discount_rate in sorted(
            self.fee_config['volume_discount_tiers'].items(),
            reverse=True
        ):
            if user_volume >= volume_threshold:
                fee_rate = discount_rate
                break
                
        # Calculate fee
        fee = amount * fee_rate
        
        # Apply min/max constraints
        fee = max(self.fee_config['min_fee'], min(self.fee_config['max_fee'], fee))
        
        return fee

    @handle_exceptions
    async def create_transaction(
        self,
        buyer_id: str,
        seller_id: str,
        agent_id: str,
        amount: Decimal,
        listing_id: Optional[str] = None
    ) -> str:
        """Create a new transaction"""
        # Validate participants
        if buyer_id == seller_id:
            raise CustomException(
                "TRANS_001",
                "Buyer and seller cannot be the same"
            )
            
        # Validate amount
        if not self.validator.validate_token_amount(float(amount)):
            raise CustomException(
                "TRANS_002",
                "Invalid transaction amount"
            )
            
        # Calculate fee
        buyer_volume = sum(
            Decimal(str(self.transactions[tid]['amount']))
            for tid in self.user_transactions.get(buyer_id, [])
            if self.transactions[tid]['state'] == TransactionState.COMPLETED
        )
        
        fee = self._calculate_fee(amount, buyer_volume)
        total_amount = amount + fee
        
        # Check buyer's balance
        if not await self.token_manager.check_balance(buyer_id, float(total_amount)):
            raise CustomException(
                "TRANS_003",
                "Insufficient balance",
                {
                    "required": float(total_amount),
                    "fee": float(fee)
                }
            )
            
        # Create transaction record
        transaction_id = str(uuid.uuid4())
        transaction = {
            'transaction_id': transaction_id,
            'buyer_id': buyer_id,
            'seller_id': seller_id,
            'agent_id': agent_id,
            'listing_id': listing_id,
            'amount': amount,
            'fee': fee,
            'total_amount': total_amount,
            'state': TransactionState.PENDING,
            'created_at': datetime.utcnow().timestamp(),
            'completed_at': None,
            'error': None
        }
        
        # Store transaction
        self.transactions[transaction_id] = transaction
        
        # Update indices
        if buyer_id not in self.user_transactions:
            self.user_transactions[buyer_id] = []
        self.user_transactions[buyer_id].append(transaction_id)
        
        if seller_id not in self.user_transactions:
            self.user_transactions[seller_id] = []
        self.user_transactions[seller_id].append(transaction_id)
        
        if agent_id not in self.agent_transactions:
            self.agent_transactions[agent_id] = []
        self.agent_transactions[agent_id].append(transaction_id)
        
        # Start processing
        process_task = asyncio.create_task(
            self._process_transaction(transaction_id)
        )
        self.active_transactions[transaction_id] = process_task
        
        # Update metrics
        self.metrics['total_transactions'] += 1
        
        logger.info(f"Created transaction {transaction_id} for agent {agent_id}")
        return transaction_id

    async def _process_transaction(self, transaction_id: str) -> None:
        """Process a transaction"""
        transaction = self.transactions[transaction_id]
        start_time = datetime.utcnow().timestamp()
        
        try:
            # Update state
            transaction['state'] = TransactionState.PROCESSING
            
            # Transfer fee
            await self.token_manager.transfer(
                transaction['buyer_id'],
                'marketplace_treasury',
                float(transaction['fee'])
            )
            
            # Transfer amount to seller
            await self.token_manager.transfer(
                transaction['buyer_id'],
                transaction['seller_id'],
                float(transaction['amount'])
            )
            
            # Transfer agent ownership
            await self.agent_manager.update_agent_ownership(
                transaction['agent_id'],
                transaction['seller_id'],
                transaction['buyer_id']
            )
            
            # Complete transaction
            transaction['state'] = TransactionState.COMPLETED
            transaction['completed_at'] = datetime.utcnow().timestamp()
            
            # Update metrics
            self.metrics['successful_transactions'] += 1
            self.metrics['total_volume'] += transaction['amount']
            self.metrics['total_fees'] += transaction['fee']
            
            completion_time = transaction['completed_at'] - start_time
            total_successful = self.metrics['successful_transactions']
            self.metrics['average_completion_time'] = (
                (self.metrics['average_completion_time'] * (total_successful - 1) +
                 completion_time) / total_successful
            )
            
            logger.info(f"Completed transaction {transaction_id}")
            
        except Exception as e:
            logger.error(f"Transaction {transaction_id} failed: {str(e)}")
            transaction['state'] = TransactionState.FAILED
            transaction['error'] = str(e)
            self.metrics['failed_transactions'] += 1
            
        finally:
            self.active_transactions.pop(transaction_id, None)

    @handle_exceptions
    async def get_transaction(
        self,
        transaction_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Get transaction details"""
        if transaction_id not in self.transactions:
            raise CustomException(
                "TRANS_004",
                "Transaction not found"
            )
            
        transaction = self.transactions[transaction_id]
        
        # Verify access permission
        if user_id not in [transaction['buyer_id'], transaction['seller_id']]:
            raise CustomException(
                "TRANS_005",
                "Unauthorized transaction access"
            )
            
        return transaction

    @handle_exceptions
    async def get_user_transactions(
        self,
        user_id: str,
        role: Optional[str] = None,
        state: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        offset: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get user's transactions with filters"""
        if user_id not in self.user_transactions:
            return []
            
        transactions = []
        for tid in self.user_transactions[user_id]:
            transaction = self.transactions[tid]
            
            # Apply role filter
            if role:
                if (role == 'buyer' and transaction['buyer_id'] != user_id or
                    role == 'seller' and transaction['seller_id'] != user_id):
                    continue
                    
            # Apply state filter
            if state and transaction['state'] != state:
                continue
                
            # Apply time filters
            if start_time and transaction['created_at'] < start_time:
                continue
            if end_time and transaction['created_at'] > end_time:
                continue
                
            transactions.append(transaction)
            
        # Sort by creation time (newest first)
        transactions.sort(key=lambda x: x['created_at'], reverse=True)
        
        return transactions[offset:offset + limit]

    @handle_exceptions
    async def dispute_transaction(
        self,
        transaction_id: str,
        user_id: str,
        reason: str
    ) -> bool:
        """Open a dispute for a transaction"""
        if transaction_id not in self.transactions:
            raise CustomException(
                "TRANS_004",
                "Transaction not found"
            )
            
        transaction = self.transactions[transaction_id]
        
        # Verify user is buyer or seller
        if user_id not in [transaction['buyer_id'], transaction['seller_id']]:
            raise CustomException(
                "TRANS_005",
                "Unauthorized transaction access"
            )
            
        # Check if transaction can be disputed
        if transaction['state'] not in [TransactionState.COMPLETED, TransactionState.FAILED]:
            raise CustomException(
                "TRANS_006",
                "Transaction cannot be disputed in current state"
            )
            
        # Update transaction state
        transaction['state'] = TransactionState.DISPUTED
        transaction['dispute'] = {
            'opened_by': user_id,
            'reason': reason,
            'opened_at': datetime.utcnow().timestamp(),
            'resolution': None
        }
        
        # Update metrics
        total_completed = (
            self.metrics['successful_transactions'] +
            self.metrics['failed_transactions']
        )
        if total_completed > 0:
            disputed_count = len([
                t for t in self.transactions.values()
                if t['state'] == TransactionState.DISPUTED
            ])
            self.metrics['dispute_rate'] = disputed_count / total_completed
            
        logger.info(f"Dispute opened for transaction {transaction_id}")
        return True

    @handle_exceptions
    async def resolve_dispute(
        self,
        transaction_id: str,
        resolution: str,
        refund: bool = False
    ) -> bool:
        """Resolve a disputed transaction"""
        if transaction_id not in self.transactions:
            raise CustomException(
                "TRANS_004",
                "Transaction not found"
            )
            
        transaction = self.transactions[transaction_id]
        
        if transaction['state'] != TransactionState.DISPUTED:
            raise CustomException(
                "TRANS_007",
                "Transaction is not disputed"
            )
            
        # Process refund if required
        if refund:
            try:
                # Return amount to buyer
                await self.token_manager.transfer(
                    transaction['seller_id'],
                    transaction['buyer_id'],
                    float(transaction['amount'])
                )
                
                # Return fee
                await self.token_manager.transfer(
                    'marketplace_treasury',
                    transaction['buyer_id'],
                    float(transaction['fee'])
                )
                
                # Revert agent ownership
                await self.agent_manager.update_agent_ownership(
                    transaction['agent_id'],
                    transaction['buyer_id'],
                    transaction['seller_id']
                )
                
                transaction['state'] = TransactionState.REFUNDED
                
            except Exception as e:
                logger.error(f"Refund failed for transaction {transaction_id}: {str(e)}")
                raise CustomException(
                    "TRANS_008",
                    "Refund failed",
                    {"error": str(e)}
                )
                
        # Update dispute resolution
        transaction['dispute']['resolution'] = {
            'outcome': resolution,
            'refunded': refund,
            'resolved_at': datetime.utcnow().timestamp()
        }
        
        logger.info(f"Resolved dispute for transaction {transaction_id}")
        return True

    def __str__(self) -> str:
        return f"TransactionManager(total={self.metrics['total_transactions']})"

    def __repr__(self) -> str:
        return (f"TransactionManager(total={self.metrics['total_transactions']}, "
                f"success_rate={self.metrics['successful_transactions']/self.metrics['total_transactions']:.2%}, "
                f"volume={float(self.metrics['total_volume']):.2f})")
