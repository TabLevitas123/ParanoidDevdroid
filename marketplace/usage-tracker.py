# services/pricing/usage_tracker.py

from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio
import json

from utils.logger import CustomLogger
from utils.error_handler import CustomException, handle_exceptions

logger = CustomLogger("usage_tracker", "usage.log")

class UsageMetrics:
    """Tracks and stores usage metrics"""
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_tokens = 0
        self.total_characters = 0
        self.total_images = 0
        self.total_cost = Decimal('0')
        self.last_updated = datetime.utcnow()

class ServiceUsage:
    """Tracks usage for specific services"""
    def __init__(self, service_type: str):
        self.service_type = service_type
        self.daily_usage = defaultdict(UsageMetrics)
        self.monthly_usage = defaultdict(UsageMetrics)
        self.model_usage = defaultdict(UsageMetrics)

class UserUsage:
    """Tracks usage per user"""
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.service_usage = defaultdict(lambda: ServiceUsage)
        self.total_spent = Decimal('0')
        self.last_activity = datetime.utcnow()

class UsageTracker:
    """Main usage tracking system"""
    def __init__(self):
        self.user_usage: Dict[str, UserUsage] = {}
        self.global_metrics = UsageMetrics()
        
        # Aggregation intervals
        self.daily_retention = 30  # days
        self.monthly_retention = 12  # months
        
        # Usage limits
        self.user_limits = {
            'daily_requests': 1000,
            'daily_tokens': 100000,
            'daily_images': 100,
            'monthly_cost': Decimal('1000')
        }

    @handle_exceptions
    async def track_request(
        self,
        user_id: str,
        service_type: str,
        model: str,
        request_data: Dict[str, Any],
        success: bool,
        cost: Decimal
    ) -> None:
        """Track a service request"""
        current_time = datetime.utcnow()
        
        # Initialize user tracking if needed
        if user_id not in self.user_usage:
            self.user_usage[user_id] = UserUsage(user_id)
        
        user = self.user_usage[user_id]
        service = user.service_usage[service_type]
        
        # Get time periods
        day_key = current_time.strftime('%Y-%m-%d')
        month_key = current_time.strftime('%Y-%m')
        
        # Update metrics
        await self._update_metrics(
            service.daily_usage[day_key],
            service.monthly_usage[month_key],
            service.model_usage[model],
            self.global_metrics,
            request_data,
            success,
            cost
        )
        
        # Update user totals
        user.total_spent += cost
        user.last_activity = current_time
        
        # Cleanup old data periodically
        if current_time.hour == 0 and current_time.minute == 0:
            await self._cleanup_old_data()

    async def _update_metrics(
        self,
        daily: UsageMetrics,
        monthly: UsageMetrics,
        model: UsageMetrics,
        global_metrics: UsageMetrics,
        request_data: Dict[str, Any],
        success: bool,
        cost: Decimal
    ) -> None:
        """Update various metric levels"""
        metrics_list = [daily, monthly, model, global_metrics]
        
        for metrics in metrics_list:
            metrics.total_requests += 1
            if success:
                metrics.successful_requests += 1
            else:
                metrics.failed_requests += 1
            
            metrics.total_cost += cost
            metrics.last_updated = datetime.utcnow()
            
            # Update specific counters based on request type
            if 'tokens' in request_data:
                metrics.total_tokens += request_data['tokens']
            if 'characters' in request_data:
                metrics.total_characters += request_data['characters']
            if 'images' in request_data:
                metrics.total_images += request_data['images']

    @handle_exceptions
    async def check_limits(
        self,
        user_id: str,
        service_type: str,
        request_data: Dict[str, Any]
    ) -> bool:
        """Check if request is within usage limits"""
        if user_id not in self.user_usage:
            return True
            
        user = self.user_usage[user_id]
        service = user.service_usage[service_type]
        current_day = datetime.utcnow().strftime('%Y-%m-%d')
        current_month = datetime.utcnow().strftime('%Y-%m')
        
        daily_metrics = service.daily_usage[current_day]
        monthly_metrics = service.monthly_usage[current_month]
        
        # Check daily request limit
        if daily_metrics.total_requests >= self.user_limits['daily_requests']:
            raise CustomException(
                "USAGE_001",
                "Daily request limit exceeded",
                {"limit": self.user_limits['daily_requests']}
            )
            
        # Check daily token limit
        if 'tokens' in request_data:
            if (daily_metrics.total_tokens + request_data['tokens'] >
                self.user_limits['daily_tokens']):
                raise CustomException(
                    "USAGE_002",
                    "Daily token limit exceeded",
                    {"limit": self.user_limits['daily_tokens']}
                )
                
        # Check daily image limit
        if 'images' in request_data:
            if (daily_metrics.total_images + request_data['images'] >
                self.user_limits['daily_images']):
                raise CustomException(
                    "USAGE_003",
                    "Daily image generation limit exceeded",
                    {"limit": self.user_limits['daily_images']}
                )
                
        # Check monthly cost limit
        if monthly_metrics.total_cost >= self.user_limits['monthly_cost']:
            raise CustomException(
                "USAGE_004",
                "Monthly cost limit exceeded",
                {"limit": float(self.user_limits['monthly_cost'])}
            )
            
        return True

    @handle_exceptions
    async def get_user_usage(
        self,
        user_id: str,
        period: str = 'day'
    ) -> Dict[str, Any]:
        """Get usage statistics for a user"""
        if user_id not in self.user_usage:
            raise CustomException(
                "USAGE_005",
                "No usage data found for user"
            )
            
        user = self.user_usage[user_id]
        current_time = datetime.utcnow()
        
        if period == 'day':
            day_key = current_time.strftime('%Y-%m-%d')
            usage_data = {
                service_type: {
                    'requests': service.daily_usage[day_key].total_requests,
                    'successful': service.daily_usage[day_key].successful_requests,
                    'failed': service.daily_usage[day_key].failed_requests,
                    'tokens': service.daily_usage[day_key].total_tokens,
                    'characters': service.daily_usage[day_key].total_characters,
                    'images': service.daily_usage[day_key].total_images,
                    'cost': float(service.daily_usage[day_key].total_cost)
                }
                for service_type, service in user.service_usage.items()
            }
        elif period == 'month':
            month_key = current_time.strftime('%Y-%m')
            usage_data = {
                service_type: {
                    'requests': service.monthly_usage[month_key].total_requests,
                    'successful': service.monthly_usage[month_key].successful_requests,
                    'failed': service.monthly_usage[month_key].failed_requests,
                    'tokens': service.monthly_usage[month_key].total_tokens,
                    'characters': service.monthly_usage[month_key].total_characters,
                    'images': service.monthly_usage[month_key].total_images,
                    'cost': float(service.monthly_usage[month_key].total_cost)
                }
                for service_type, service in user.service_usage.items()
            }
        else:
            raise CustomException(
                "USAGE_006",
                "Invalid period specified",
                {"valid_periods": ['day', 'month']}
            )
            
        return {
            'period': period,
            'services': usage_data,
            'total_spent': float(user.total_spent),
            'last_activity': user.last_activity.isoformat()
        }

    @handle_exceptions
    async def get_service_usage(
        self,
        service_type: str,
        period: str = 'day'
    ) -> Dict[str, Any]:
        """Get usage statistics for a service"""
        current_time = datetime.utcnow()
        
        # Aggregate usage across all users
        total_metrics = UsageMetrics()
        model_usage = defaultdict(UsageMetrics)
        
        for user in self.user_usage.values():
            if service_type in user.service_usage:
                service = user.service_usage[service_type]
                
                if period == 'day':
                    day_key = current_time.strftime('%Y-%m-%d')
                    metrics = service.daily_usage[day_key]
                elif period == 'month':
                    month_key = current_time.strftime('%Y-%m')
                    metrics = service.monthly_usage[month_key]
                else:
                    raise CustomException(
                        "USAGE_006",
                        "Invalid period specified",
                        {"valid_periods": ['day', 'month']}
                    )
                
                # Update totals
                total_metrics.total_requests += metrics.total_requests
                total_metrics.successful_requests += metrics.successful_requests
                total_metrics.failed_requests += metrics.failed_requests
                total_metrics.total_tokens += metrics.total_tokens
                total_metrics.total_characters += metrics.total_characters
                total_metrics.total_images += metrics.total_images
                total_metrics.total_cost += metrics.total_cost
                
                # Aggregate model usage
                for model, model_metrics in service.model_usage.items():
                    model_metrics_copy = model_usage[model]
                    model_metrics_copy.total_requests += model_metrics.total_requests
                    model_metrics_copy.successful_requests += model_metrics.successful_requests
                    model_metrics_copy.failed_requests += model_metrics.failed_requests
                    model_metrics_copy.total_cost += model_metrics.total_cost
        
        return {
            'period': period,
            'total': {
                'requests': total_metrics.total_requests,
                'successful': total_metrics.successful_requests,
                'failed': total_metrics.failed_requests,
                'tokens': total_metrics.total_tokens,
                'characters': total_metrics.total_characters,
                'images': total_metrics.total_images,
                'cost': float(total_metrics.total_cost)
            },
            'models': {
                model: {
                    'requests': metrics.total_requests,
                    'successful': metrics.successful_requests,
                    'failed': metrics.failed_requests,
                    'cost': float(metrics.total_cost)
                }
                for model, metrics in model_usage.items()
            }
        }

    async def _cleanup_old_data(self) -> None:
        """Remove old usage data"""
        current_time = datetime.utcnow()
        cutoff_daily = current_time - timedelta(days=self.daily_retention)
        cutoff_monthly = current_time - timedelta(days=30 * self.monthly_retention)
        
        for user in self.user_usage.values():
            for service in user.service_usage.values():
                # Clean daily data
                service.daily_usage = defaultdict(
                    UsageMetrics,
                    {
                        day: metrics
                        for day, metrics in service.daily_usage.items()
                        if datetime.strptime(day, '%Y-%m-%d') > cutoff_daily
                    }
                )
                
                # Clean monthly data
                service.monthly_usage = defaultdict(
                    UsageMetrics,
                    {
                        month: metrics
                        for month, metrics in service.monthly_usage.items()
                        if datetime.strptime(month, '%Y-%m') > cutoff_monthly
                    }
                )

    @handle_exceptions
    async def update_limits(
        self,
        new_limits: Dict[str, Any]
    ) -> bool:
        """Update usage limits"""
        valid_limits = {
            'daily_requests',
            'daily_tokens',
            'daily_images',
            'monthly_cost'
        }
        
        invalid_limits = set(new_limits.keys()) - valid_limits
        if invalid_limits:
            raise CustomException(
                "USAGE_007",
                "Invalid limits specified",
                {"invalid_limits": list(invalid_limits)}
            )
            
        for limit, value in new_limits.items():
            if limit == 'monthly_cost':
                self.user_limits[limit] = Decimal(str(value))
            else:
                self.user_limits[limit] = int(value)
                
        logger.info(f"Updated usage limits: {self.user_limits}")
        return True

    def __str__(self) -> str:
        return f"UsageTracker(users={len(self.user_usage)})"

    def __repr__(self) -> str:
        return (f"UsageTracker(users={len(self.user_usage)}, "
                f"limits={self.user_limits})")
