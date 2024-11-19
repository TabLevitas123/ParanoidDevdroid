# mock_blockchain.py

from typing import Dict, Any
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class MockBlockchain:
    """Mock blockchain for testing"""
    def __init__(self):
        self.balances: Dict[str, Decimal] = {}
        self.transactions: list = []
        
    async def get_balance(self, address: str) -> Decimal:
        """Get balance for address"""
        return self.balances.get(address, Decimal('0'))
        
    async def transfer(
        self,
        from_address: str,
        to_address: str,
        amount: Decimal
    ) -> Dict[str, Any]:
        """Mock token transfer"""
        if from_address not in self.balances:
            self.balances[from_address] = Decimal('1000')  # Give initial balance for testing
            
        if self.balances[from_address] < amount:
            raise ValueError("Insufficient balance")
            
        # Process transfer
        self.balances[from_address] -= amount
        if to_address not in self.balances:
            self.balances[to_address] = Decimal('0')
        self.balances[to_address] += amount
        
        # Record transaction
        tx = {
            'from': from_address,
            'to': to_address,
            'amount': amount,
            'status': 'success'
        }
        self.transactions.append(tx)
        
        return {
            'success': True,
            'transaction': tx
        }
        
    async def create_wallet(self) -> Dict[str, str]:
        """Create mock wallet"""
        import uuid
        address = f"0x{uuid.uuid4().hex}"
        self.balances[address] = Decimal('1000')  # Initial balance
        return {
            'address': address,
            'private_key': f"mock_key_{address}"
        }

# Global mock blockchain instance for testing
mock_blockchain = MockBlockchain()
