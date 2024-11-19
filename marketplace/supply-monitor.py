# services/pricing/supply_monitor.py

from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict

from utils.logger import CustomLogger
from utils.error_handler import CustomException, handle_exceptions

logger = CustomLogger("supply_monitor", "pricing.log")

@dataclass
class ServiceCapacity:
    """Tracks capacity metrics for a service"""
    total_capacity: int
    used_capacity: int
    reserved_capacity: int
    maintenance_window: Optional[tuple[datetime, datetime]] = None
    degraded_performance: bool = False
    last_updated: datetime = datetime.utcnow()

    @property
    def available_capacity(self) -> int:
        """Calculate currently available capacity"""
        return max(0, self.total_capacity - self.used_capacity - self.reserved_capacity)

    @property
    def utilization_rate(self) -> float:
        """Calculate current utilization rate"""
        if self.total_capacity == 0:
            return 0.0
        return (self.used_capacity + self.reserved_capacity) / self.total_capacity

class ServiceHealth:
    """Tracks service health metrics"""
    def __init__(self):
        self.error_count: int = 0
        self.total_requests: int = 0
        self.response_times: List[float] = []
        self.last_error: Optional[datetime] = None
        self.degraded_since: Optional[datetime] = None
        
    @property
    def error_rate(self) -> float:
        """Calculate current error rate"""
        if self.total_requests == 0:
            return 0.0
        return self.error_count / self.total_requests

    @property
    def avg_response_time(self) -> float:
        """Calculate average response time"""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)

    def is_healthy(self, error_threshold: float = 0.05) -> bool:
        """Check if service is healthy"""
        return self.error_rate <= error_threshold

class SupplyMonitor:
    """Monitors service supply and capacity"""
    def __init__(self):
        # Service capacities
        self.service_capacity: Dict[str, Dict[str, ServiceCapacity]] = defaultdict(dict)
        
        # Service health tracking
        self.service_health: Dict[str, Dict[str, ServiceHealth]] = defaultdict(
            lambda: defaultdict(ServiceHealth)
        )
        
        # Configuration
        self.config = {
            'capacity_buffer': 0.1,  # 10% buffer
            'health_window': 3600,  # 1 hour
            'max_response_samples': 1000,
            'error_threshold': 0.05,  # 5% error rate threshold
            'degraded_threshold': 0.8  # 80% capacity threshold
        }

    @handle_exceptions
    async def register_service(
        self,
        service_type: str,
        model: str,
        capacity: int
    ) -> None:
        """Register a new service with its capacity"""
        if capacity <= 0:
            raise CustomException(
                "SUPPLY_001",
                "Invalid capacity value",
                {"capacity": capacity}
            )
            
        self.service_capacity[service_type][model] = ServiceCapacity(
            total_capacity=capacity,
            used_capacity=0,
            reserved_capacity=int(capacity * self.config['capacity_buffer'])
        )
        
        logger.info(f"Registered service {service_type}/{model} with capacity {capacity}")

    @handle_exceptions
    async def update_capacity(
        self,
        service_type: str,
        model: str,
        new_capacity: int
    ) -> None:
        """Update service capacity"""
        if service_type not in self.service_capacity or model not in self.service_capacity[service_type]:
            raise CustomException(
                "SUPPLY_002",
                "Service not found",
                {"service": f"{service_type}/{model}"}
            )
            
        if new_capacity <= 0:
            raise CustomException(
                "SUPPLY_001",
                "Invalid capacity value",
                {"capacity": new_capacity}
            )
            
        capacity = self.service_capacity[service_type][model]
        capacity.total_capacity = new_capacity
        capacity.reserved_capacity = int(new_capacity * self.config['capacity_buffer'])
        capacity.last_updated = datetime.utcnow()
        
        logger.info(f"Updated capacity for {service_type}/{model} to {new_capacity}")

    @handle_exceptions
    async def allocate_capacity(
        self,
        service_type: str,
        model: str,
        amount: int
    ) -> bool:
        """Attempt to allocate capacity for a request"""
        if service_type not in self.service_capacity or model not in self.service_capacity[service_type]:
            raise CustomException(
                "SUPPLY_002",
                "Service not found",
                {"service": f"{service_type}/{model}"}
            )
            
        capacity = self.service_capacity[service_type][model]
        
        if amount <= 0:
            raise CustomException(
                "SUPPLY_003",
                "Invalid allocation amount",
                {"amount": amount}
            )
            
        if capacity.available_capacity < amount:
            return False
            
        capacity.used_capacity += amount
        capacity.last_updated = datetime.utcnow()
        
        # Check for degraded performance
        if capacity.utilization_rate >= self.config['degraded_threshold']:
            capacity.degraded_performance = True
            
        return True

    @handle_exceptions
    async def release_capacity(
        self,
        service_type: str,
        model: str,
        amount: int
    ) -> None:
        """Release allocated capacity"""
        if service_type not in self.service_capacity or model not in self.service_capacity[service_type]:
            raise CustomException(
                "SUPPLY_002",
                "Service not found",
                {"service": f"{service_type}/{model}"}
            )
            
        capacity = self.service_capacity[service_type][model]
        
        if amount <= 0:
            raise CustomException(
                "SUPPLY_003",
                "Invalid release amount",
                {"amount": amount}
            )
            
        capacity.used_capacity = max(0, capacity.used_capacity - amount)
        capacity.last_updated = datetime.utcnow()
        
        # Check if we can clear degraded status
        if capacity.utilization_rate < self.config['degraded_threshold']:
            capacity.degraded_performance = False

    @handle_exceptions
    async def record_health_metrics(
        self,
        service_type: str,
        model: str,
        success: bool,
        response_time: float
    ) -> None:
        """Record health metrics for a service request"""
        health = self.service_health[service_type][model]
        current_time = datetime.utcnow()
        
        # Update counters
        health.total_requests += 1
        if not success:
            health.error_count += 1
            health.last_error = current_time
        
        # Update response times
        health.response_times.append(response_time)
        if len(health.response_times) > self.config['max_response_samples']:
            health.response_times.pop(0)
        
        # Check health status
        if not health.is_healthy(self.config['error_threshold']):
            if not health.degraded_since:
                health.degraded_since = current_time
                logger.warning(f"Service {service_type}/{model} entered degraded state")

    @handle_exceptions
    async def schedule_maintenance(
        self,
        service_type: str,
        model: str,
        start_time: datetime,
        end_time: datetime
    ) -> None:
        """Schedule maintenance window for a service"""
        if service_type not in self.service_capacity or model not in self.service_capacity[service_type]:
            raise CustomException(
                "SUPPLY_002",
                "Service not found",
                {"service": f"{service_type}/{model}"}
            )
            
        if start_time >= end_time:
            raise CustomException(
                "SUPPLY_004",
                "Invalid maintenance window",
                {"start": start_time, "end": end_time}
            )
            
        capacity = self.service_capacity[service_type][model]
        capacity.maintenance_window = (start_time, end_time)
        logger.info(f"Scheduled maintenance for {service_type}/{model}: {start_time} to {end_time}")

    @handle_exceptions
    async def get_supply_status(
        self,
        service_type: str,
        model: str
    ) -> Dict[str, Any]:
        """Get current supply status for a service"""
        if service_type not in self.service_capacity or model not in self.service_capacity[service_type]:
            raise CustomException(
                "SUPPLY_002",
                "Service not found",
                {"service": f"{service_type}/{model}"}
            )
            
        capacity = self.service_capacity[service_type][model]
        health = self.service_health[service_type][model]
        
        return {
            'capacity': {
                'total': capacity.total_capacity,
                'used': capacity.used_capacity,
                'reserved': capacity.reserved_capacity,
                'available': capacity.available_capacity,
                'utilization_rate': capacity.utilization_rate,
                'degraded': capacity.degraded_performance,
                'last_updated': capacity.last_updated.isoformat()
            },
            'health': {
                'error_rate': health.error_rate,
                'total_requests': health.total_requests,
                'avg_response_time': health.avg_response_time,
                'last_error': health.last_error.isoformat() if health.last_error else None,
                'degraded_since': health.degraded_since.isoformat() if health.degraded_since else None
            },
            'maintenance': {
                'scheduled': bool(capacity.maintenance_window),
                'window': {
                    'start': capacity.maintenance_window[0].isoformat(),
                    'end': capacity.maintenance_window[1].isoformat()
                } if capacity.maintenance_window else None
            }
        }

    @handle_exceptions
    async def get_all_services_status(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Get status for all registered services"""
        return {
            service_type: {
                model: await self.get_supply_status(service_type, model)
                for model in models
            }
            for service_type, models in self.service_capacity.items()
        }

    def __str__(self) -> str:
        return f"SupplyMonitor(services={len(self.service_capacity)})"

    def __repr__(self) -> str:
        return (f"SupplyMonitor(services={len(self.service_capacity)}, "
                f"config={self.config})")
