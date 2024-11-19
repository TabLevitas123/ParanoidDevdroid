# tokens/dynamic_stabilizer.py

from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
import asyncio
from datetime import datetime, timedelta
import statistics
from collections import deque

from config.constants import TokenType
from utils.logger import CustomLogger
from utils.error_handler import CustomException, handle_exceptions
from tokens.token_manager import TokenManager

logger = CustomLogger("dynamic_stabilizer", "token_stabilizer.log")

class DynamicStabilizer:
    def __init__(
        self,
        token_manager: TokenManager,
        target_price: Decimal = Decimal('1.0'),
        price_tolerance: Decimal = Decimal('0.02'),
        adjustment_interval: int = 3600,  # 1 hour in seconds
        max_adjustment: Decimal = Decimal('0.05')  # 5% max adjustment
    ):
        self.token_manager = token_manager
        self.target_price = target_price
        self.price_tolerance = price_tolerance
        self.adjustment_interval = adjustment_interval
        self.max_adjustment = max_adjustment
        
        # Market data tracking
        self.price_history: deque = deque(maxlen=1000)
        self.volume_history: deque = deque(maxlen=1000)
        self.last_adjustment_time = datetime.utcnow()
        
        # Stabilization metrics
        self.metrics = {
            'total_adjustments': 0,
            'successful_adjustments': 0,
            'failed_adjustments': 0,
            'total_supply_changes': Decimal('0'),
            'max_price_deviation': Decimal('0'),
            'average_adjustment_size': Decimal('0'),
            'price_volatility': Decimal('0')
        }
        
        # Control parameters
        self.control_params = {
            'kp': Decimal('0.5'),  # Proportional gain
            'ki': Decimal('0.1'),  # Integral gain
            'kd': Decimal('0.2'),  # Derivative gain
            'integral_error': Decimal('0'),
            'last_error': Decimal('0'),
            'damping_factor': Decimal('0.8')
        }
        
        # Market state
        self.market_state = {
            'current_price': target_price,
            'current_supply': Decimal('0'),
            'demand_rate': Decimal('0'),
            'supply_rate': Decimal('0'),
            'liquidity_depth': Decimal('0')
        }

    @handle_exceptions
    async def initialize(self) -> bool:
        """Initialize stabilizer with current market state"""
        try:
            # Get initial market state
            current_supply = await self._get_total_supply()
            current_price = await self._get_current_price()
            
            self.market_state.update({
                'current_supply': current_supply,
                'current_price': current_price
            })
            
            self.price_history.append((datetime.utcnow(), current_price))
            logger.info(f"Stabilizer initialized with price: {current_price}, supply: {current_supply}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize stabilizer: {str(e)}")
            raise CustomException(
                "STAB_001",
                "Stabilizer initialization failed",
                {"error": str(e)}
            )

    @handle_exceptions
    async def update_market_state(
        self,
        new_transactions: List[Dict[str, Any]]
    ) -> None:
        """Update market state with new transaction data"""
        if not new_transactions:
            return
            
        try:
            # Calculate volume and price metrics
            total_volume = sum(
                Decimal(str(tx['amount']))
                for tx in new_transactions
                if tx['token_type'] == TokenType.UTILITY
            )
            
            weighted_price = sum(
                Decimal(str(tx['amount'])) * Decimal(str(tx['price']))
                for tx in new_transactions
                if tx['token_type'] == TokenType.UTILITY
            ) / total_volume if total_volume > 0 else self.market_state['current_price']
            
            current_time = datetime.utcnow()
            self.price_history.append((current_time, weighted_price))
            self.volume_history.append((current_time, total_volume))
            
            # Update market state
            self.market_state.update({
                'current_price': weighted_price,
                'current_supply': await self._get_total_supply(),
                'demand_rate': self._calculate_demand_rate(),
                'supply_rate': self._calculate_supply_rate(),
                'liquidity_depth': self._calculate_liquidity_depth()
            })
            
            # Log significant price changes
            price_change = abs(weighted_price - self.target_price) / self.target_price
            if price_change > self.price_tolerance:
                logger.warning(
                    f"Significant price deviation detected: {price_change:.2%} "
                    f"from target price"
                )
            
        except Exception as e:
            logger.error(f"Failed to update market state: {str(e)}")
            raise CustomException(
                "STAB_002",
                "Market state update failed",
                {"error": str(e)}
            )

    async def _get_total_supply(self) -> Decimal:
        """Get current total supply of utility tokens"""
        try:
            contract_address = self.token_manager.token_contracts[TokenType.UTILITY]
            result = await self.token_manager.smart_contract_manager.send_transaction(
                "totalSupply",
                tuple(),
                None
            )
            
            if not result['success']:
                raise CustomException(
                    "STAB_003",
                    "Failed to get total supply",
                    {"error": result.get('error')}
                )
                
            return Decimal(str(result['data']))
            
        except Exception as e:
            logger.error(f"Failed to get total supply: {str(e)}")
            raise

    async def _get_current_price(self) -> Decimal:
        """Get current market price from oracle or price feed"""
        # Implementation would connect to price oracle
        # For now, using last known price or target price
        if self.price_history:
            return self.price_history[-1][1]
        return self.target_price

    def _calculate_demand_rate(self) -> Decimal:
        """Calculate current token demand rate"""
        if len(self.volume_history) < 2:
            return Decimal('0')
            
        recent_volumes = [
            volume for _, volume in self.volume_history
            if datetime.utcnow() - timedelta(hours=1) <= timestamp
        ]
        
        return sum(recent_volumes) / len(recent_volumes) if recent_volumes else Decimal('0')

    def _calculate_supply_rate(self) -> Decimal:
        """Calculate current token supply rate"""
        if len(self.price_history) < 2:
            return Decimal('0')
            
        time_delta = (self.price_history[-1][0] - self.price_history[0][0]).total_seconds()
        supply_delta = self.market_state['current_supply'] - self._get_initial_supply()
        
        return supply_delta / time_delta if time_delta > 0 else Decimal('0')

    def _calculate_liquidity_depth(self) -> Decimal:
        """Calculate market liquidity depth"""
        recent_volumes = [
            volume for _, volume in self.volume_history
            if datetime.utcnow() - timedelta(hours=24) <= timestamp
        ]
        
        return Decimal(str(sum(recent_volumes) / len(recent_volumes))) if recent_volumes else Decimal('0')

    def _get_initial_supply(self) -> Decimal:
        """Get initial token supply"""
        return Decimal('1000000')  # Example initial supply

    @handle_exceptions
    async def check_and_adjust(self) -> Optional[Dict[str, Any]]:
        """Check if price adjustment is needed and perform if necessary"""
        current_time = datetime.utcnow()
        
        # Check if enough time has passed since last adjustment
        if (current_time - self.last_adjustment_time).total_seconds() < self.adjustment_interval:
            return None
            
        try:
            # Calculate price deviation
            current_price = self.market_state['current_price']
            price_error = (current_price - self.target_price) / self.target_price
            
            # Check if adjustment is needed
            if abs(price_error) <= self.price_tolerance:
                return None
                
            # Calculate PID control terms
            p_term = self.control_params['kp'] * price_error
            self.control_params['integral_error'] += price_error * self.adjustment_interval
            i_term = self.control_params['ki'] * self.control_params['integral_error']
            d_term = self.control_params['kd'] * (
                price_error - self.control_params['last_error']
            ) / self.adjustment_interval
            
            # Calculate adjustment
            adjustment = -(p_term + i_term + d_term) * self.control_params['damping_factor']
            
            # Limit adjustment size
            adjustment = max(min(adjustment, self.max_adjustment), -self.max_adjustment)
            
            # Calculate supply change
            current_supply = self.market_state['current_supply']
            supply_change = current_supply * adjustment
            
            # Perform adjustment
            if supply_change > 0:
                success = await self._mint_tokens(supply_change)
            else:
                success = await self._burn_tokens(-supply_change)
                
            # Update metrics
            self.metrics['total_adjustments'] += 1
            if success:
                self.metrics['successful_adjustments'] += 1
                self.metrics['total_supply_changes'] += abs(supply_change)
                self.metrics['average_adjustment_size'] = (
                    (self.metrics['average_adjustment_size'] * 
                     (self.metrics['successful_adjustments'] - 1) +
                     abs(adjustment)) /
                    self.metrics['successful_adjustments']
                )
            else:
                self.metrics['failed_adjustments'] += 1
                
            # Update state
            self.last_adjustment_time = current_time
            self.control_params['last_error'] = price_error
            
            logger.info(
                f"Price adjustment performed: {adjustment:.2%}, "
                f"supply change: {supply_change}"
            )
            
            return {
                'timestamp': current_time,
                'price_error': float(price_error),
                'adjustment': float(adjustment),
                'supply_change': float(supply_change),
                'success': success
            }
            
        except Exception as e:
            logger.error(f"Failed to perform price adjustment: {str(e)}")
            raise CustomException(
                "STAB_004",
                "Price adjustment failed",
                {"error": str(e)}
            )

    async def _mint_tokens(self, amount: Decimal) -> bool:
        """Mint new utility tokens"""
        try:
            result = await self.token_manager.smart_contract_manager.send_transaction(
                "mint",
                (amount,),
                None  # Treasury wallet private key would be used here
            )
            
            return result['success']
            
        except Exception as e:
            logger.error(f"Token minting failed: {str(e)}")
            return False

    async def _burn_tokens(self, amount: Decimal) -> bool:
        """Burn utility tokens"""
        try:
            result = await self.token_manager.smart_contract_manager.send_transaction(
                "burn",
                (amount,),
                None  # Treasury wallet private key would be used here
            )
            
            return result['success']
            
        except Exception as e:
            logger.error(f"Token burning failed: {str(e)}")
            return False

    @handle_exceptions
    async def get_metrics(self) -> Dict[str, Any]:
        """Get stabilizer performance metrics"""
        current_time = datetime.utcnow()
        recent_prices = [
            price for timestamp, price in self.price_history
            if current_time - timedelta(hours=24) <= timestamp
        ]
        
        if recent_prices:
            self.metrics['price_volatility'] = Decimal(str(statistics.stdev(recent_prices)))
            self.metrics['max_price_deviation'] = max(
                abs(price - self.target_price) / self.target_price
                for price in recent_prices
            )
        
        return {
            'current_state': {
                'price': float(self.market_state['current_price']),
                'supply': float(self.market_state['current_supply']),
                'demand_rate': float(self.market_state['demand_rate']),
                'liquidity_depth': float(self.market_state['liquidity_depth'])
            },
            'adjustments': {
                'total': self.metrics['total_adjustments'],
                'successful': self.metrics['successful_adjustments'],
                'failed': self.metrics['failed_adjustments'],
                'success_rate': (
                    self.metrics['successful_adjustments'] /
                    self.metrics['total_adjustments']
                    if self.metrics['total_adjustments'] > 0 else 0
                )
            },
            'performance': {
                'total_supply_changes': float(self.metrics['total_supply_changes']),
                'max_price_deviation': float(self.metrics['max_price_deviation']),
                'average_adjustment_size': float(self.metrics['average_adjustment_size']),
                'price_volatility': float(self.metrics['price_volatility'])
            }
        }

    def __str__(self) -> str:
        return (f"DynamicStabilizer(target={self.target_price}, "
                f"current={self.market_state['current_price']:.4f}, "
                f"adjustments={self.metrics['total_adjustments']})")

    def __repr__(self) -> str:
        return (f"DynamicStabilizer(target={self.target_price}, "
                f"tolerance={self.price_tolerance}, "
                f"interval={self.adjustment_interval}, "
                f"max_adjustment={self.max_adjustment})")
