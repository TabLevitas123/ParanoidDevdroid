# services/pricing/demand_analyzer.py

from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
from dataclasses import dataclass

from utils.logger import CustomLogger
from utils.error_handler import CustomException, handle_exceptions

logger = CustomLogger("demand_analyzer", "pricing.log")

@dataclass
class DemandMetrics:
    """Container for demand-related metrics"""
    request_count: int = 0
    unique_users: int = 0
    peak_requests: int = 0
    average_requests: float = 0.0
    trend_coefficient: float = 0.0
    last_updated: datetime = datetime.utcnow()

class TimeWindow:
    """Manages time-based analysis windows"""
    def __init__(self, window_size: int = 3600):  # Default 1 hour
        self.window_size = window_size
        self.data_points: List[Dict[str, Any]] = []
        
    def add_point(self, value: int, timestamp: datetime) -> None:
        """Add a data point to the window"""
        self.data_points.append({
            'value': value,
            'timestamp': timestamp
        })
        self._cleanup()
        
    def _cleanup(self) -> None:
        """Remove data points outside the window"""
        cutoff = datetime.utcnow() - timedelta(seconds=self.window_size)
        self.data_points = [
            point for point in self.data_points
            if point['timestamp'] > cutoff
        ]
        
    def get_statistics(self) -> Dict[str, float]:
        """Calculate statistical measures for the window"""
        if not self.data_points:
            return {
                'mean': 0.0,
                'median': 0.0,
                'std_dev': 0.0,
                'min': 0.0,
                'max': 0.0
            }
            
        values = [point['value'] for point in self.data_points]
        return {
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0.0,
            'min': min(values),
            'max': max(values)
        }

class DemandAnalyzer:
    """Analyzes service demand patterns"""
    def __init__(self):
        # Time windows for different analysis periods
        self.windows = {
            'minute': TimeWindow(60),
            'hour': TimeWindow(3600),
            'day': TimeWindow(86400)
        }
        
        # Service-specific metrics
        self.service_metrics: Dict[str, Dict[str, DemandMetrics]] = defaultdict(
            lambda: defaultdict(DemandMetrics)
        )
        
        # User activity tracking
        self.active_users: Dict[str, Dict[str, datetime]] = defaultdict(dict)
        
        # Historical peaks
        self.historical_peaks: Dict[str, Dict[str, int]] = defaultdict(dict)
        
        # Seasonality patterns
        self.hourly_patterns: Dict[str, Dict[int, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        self.daily_patterns: Dict[str, Dict[int, float]] = defaultdict(
            lambda: defaultdict(float)
        )

    @handle_exceptions
    async def record_request(
        self,
        service_type: str,
        model: str,
        user_id: str,
        timestamp: Optional[datetime] = None
    ) -> None:
        """Record a service request for demand analysis"""
        timestamp = timestamp or datetime.utcnow()
        
        # Update time windows
        for window in self.windows.values():
            window.add_point(1, timestamp)
        
        # Update service metrics
        metrics = self.service_metrics[service_type][model]
        metrics.request_count += 1
        metrics.last_updated = timestamp
        
        # Update user activity
        self.active_users[service_type][user_id] = timestamp
        metrics.unique_users = len(self.active_users[service_type])
        
        # Update peak tracking
        hour_key = timestamp.strftime('%Y-%m-%d-%H')
        current_hour_requests = sum(
            1 for user_time in self.active_users[service_type].values()
            if user_time.strftime('%Y-%m-%d-%H') == hour_key
        )
        
        if current_hour_requests > metrics.peak_requests:
            metrics.peak_requests = current_hour_requests
            self.historical_peaks[service_type][hour_key] = current_hour_requests
        
        # Update pattern analysis
        await self._update_patterns(service_type, timestamp)

    async def _update_patterns(
        self,
        service_type: str,
        timestamp: datetime
    ) -> None:
        """Update seasonality patterns"""
        hour = timestamp.hour
        day = timestamp.weekday()
        
        # Update hourly pattern
        total_hourly = sum(self.hourly_patterns[service_type].values()) or 1
        self.hourly_patterns[service_type][hour] = (
            self.hourly_patterns[service_type][hour] * 0.95 + 0.05
        ) / total_hourly
        
        # Update daily pattern
        total_daily = sum(self.daily_patterns[service_type].values()) or 1
        self.daily_patterns[service_type][day] = (
            self.daily_patterns[service_type][day] * 0.95 + 0.05
        ) / total_daily

    @handle_exceptions
    async def get_current_demand(
        self,
        service_type: str,
        model: str
    ) -> Dict[str, Any]:
        """Get current demand metrics for a service"""
        metrics = self.service_metrics[service_type][model]
        current_time = datetime.utcnow()
        
        # Calculate statistics for different time windows
        window_stats = {
            window_name: window.get_statistics()
            for window_name, window in self.windows.items()
        }
        
        # Calculate trend using hour window
        hour_stats = self.windows['hour'].get_statistics()
        if hour_stats['std_dev'] > 0:
            metrics.trend_coefficient = (
                (hour_stats['mean'] - metrics.average_requests) /
                hour_stats['std_dev']
            )
        
        # Update average requests
        metrics.average_requests = (
            metrics.average_requests * 0.95 +
            hour_stats['mean'] * 0.05
        )
        
        return {
            'current': {
                'request_count': metrics.request_count,
                'unique_users': metrics.unique_users,
                'peak_requests': metrics.peak_requests,
                'average_requests': metrics.average_requests,
                'trend_coefficient': metrics.trend_coefficient
            },
            'windows': window_stats,
            'patterns': {
                'hourly': dict(self.hourly_patterns[service_type]),
                'daily': dict(self.daily_patterns[service_type])
            },
            'last_updated': metrics.last_updated.isoformat()
        }

    @handle_exceptions
    async def get_demand_forecast(
        self,
        service_type: str,
        model: str,
        hours_ahead: int = 24
    ) -> Dict[str, List[float]]:
        """Forecast demand for future time periods"""
        current_time = datetime.utcnow()
        forecast = []
        
        metrics = self.service_metrics[service_type][model]
        base_demand = metrics.average_requests
        
        for hour in range(hours_ahead):
            forecast_time = current_time + timedelta(hours=hour)
            
            # Apply hourly and daily patterns
            hour_factor = self.hourly_patterns[service_type][forecast_time.hour]
            day_factor = self.daily_patterns[service_type][forecast_time.weekday()]
            
            # Apply trend
            trend_impact = metrics.trend_coefficient * (hour / 24)
            
            # Calculate forecasted demand
            forecasted_demand = (
                base_demand *
                hour_factor *
                day_factor *
                (1 + trend_impact)
            )
            
            forecast.append(max(0, forecasted_demand))
        
        return {
            'timestamps': [
                (current_time + timedelta(hours=h)).isoformat()
                for h in range(hours_ahead)
            ],
            'values': forecast
        }

    @handle_exceptions
    async def get_demand_score(
        self,
        service_type: str,
        model: str
    ) -> float:
        """Calculate normalized demand score (0-1)"""
        metrics = self.service_metrics[service_type][model]
        
        if metrics.peak_requests == 0:
            return 0.0
            
        hour_stats = self.windows['hour'].get_statistics()
        current_demand = hour_stats['mean']
        
        # Calculate score components
        utilization_score = current_demand / metrics.peak_requests
        trend_score = max(0, min(1, (metrics.trend_coefficient + 1) / 2))
        pattern_score = self.hourly_patterns[service_type][datetime.utcnow().hour]
        
        # Combine scores with weights
        weights = {
            'utilization': 0.5,
            'trend': 0.3,
            'pattern': 0.2
        }
        
        demand_score = (
            utilization_score * weights['utilization'] +
            trend_score * weights['trend'] +
            pattern_score * weights['pattern']
        )
        
        return max(0, min(1, demand_score))

    def __str__(self) -> str:
        return f"DemandAnalyzer(services={len(self.service_metrics)})"

    def __repr__(self) -> str:
        return (f"DemandAnalyzer(services={len(self.service_metrics)}, "
                f"active_users={sum(len(users) for users in self.active_users.values())})")
