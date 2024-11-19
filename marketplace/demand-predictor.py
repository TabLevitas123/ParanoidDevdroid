# services/pricing/demand_predictor.py

from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict
import numpy as np
from scipy import stats
import statistics

from utils.logger import CustomLogger
from utils.error_handler import CustomException, handle_exceptions

logger = CustomLogger("demand_predictor", "pricing.log")

@dataclass
class TimeSeriesPoint:
    """Single point in time series data"""
    timestamp: datetime
    value: float
    features: Dict[str, float]

class TimeWindow:
    """Manages time windows for analysis"""
    def __init__(self, duration: timedelta):
        self.duration = duration
        self.data_points: List[TimeSeriesPoint] = []
        
    def add_point(self, point: TimeSeriesPoint) -> None:
        """Add data point and maintain window"""
        self.data_points.append(point)
        self._cleanup()
        
    def _cleanup(self) -> None:
        """Remove points outside window"""
        cutoff = datetime.utcnow() - self.duration
        self.data_points = [
            point for point in self.data_points
            if point.timestamp > cutoff
        ]
        
    def get_values(self) -> List[float]:
        """Get all values in window"""
        return [point.value for point in self.data_points]

class SeasonalPattern:
    """Analyzes and stores seasonal patterns"""
    def __init__(self, period: timedelta, num_buckets: int):
        self.period = period
        self.num_buckets = num_buckets
        self.patterns: Dict[int, List[float]] = defaultdict(list)
        
    def add_point(self, point: TimeSeriesPoint) -> None:
        """Add point to seasonal analysis"""
        bucket = self._get_bucket(point.timestamp)
        self.patterns[bucket].append(point.value)
        
    def _get_bucket(self, timestamp: datetime) -> int:
        """Get appropriate time bucket for timestamp"""
        total_seconds = self.period.total_seconds()
        seconds_elapsed = (
            timestamp - timestamp.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        ).total_seconds()
        return int((seconds_elapsed % total_seconds) / (total_seconds / self.num_buckets))
        
    def get_pattern(self) -> Dict[int, float]:
        """Get average pattern values"""
        return {
            bucket: statistics.mean(values) if values else 0.0
            for bucket, values in self.patterns.items()
        }

class DemandPredictor:
    """Predicts future service demand"""
    def __init__(self):
        # Time windows for different analysis periods
        self.windows = {
            'hour': TimeWindow(timedelta(hours=1)),
            'day': TimeWindow(timedelta(days=1)),
            'week': TimeWindow(timedelta(weeks=1)),
            'month': TimeWindow(timedelta(days=30))
        }
        
        # Seasonal patterns
        self.patterns = {
            'daily': SeasonalPattern(timedelta(days=1), 24),  # Hourly patterns
            'weekly': SeasonalPattern(timedelta(weeks=1), 7),  # Daily patterns
            'monthly': SeasonalPattern(timedelta(days=30), 30)  # Daily patterns
        }
        
        # Feature importance tracking
        self.feature_correlations: Dict[str, float] = {}
        
        # Model performance tracking
        self.prediction_errors: List[float] = []
        self.last_predictions: Dict[str, Tuple[float, datetime]] = {}
        
        # Configuration
        self.config = {
            'min_data_points': 24,
            'confidence_threshold': 0.8,
            'max_forecast_hours': 168,  # 1 week
            'seasonality_threshold': 0.3
        }

    @handle_exceptions
    async def record_demand(
        self,
        timestamp: datetime,
        value: float,
        features: Dict[str, float]
    ) -> None:
        """Record new demand data point"""
        point = TimeSeriesPoint(timestamp, value, features)
        
        # Add to time windows
        for window in self.windows.values():
            window.add_point(point)
        
        # Add to seasonal patterns
        for pattern in self.patterns.values():
            pattern.add_point(point)
        
        # Update feature correlations
        await self._update_feature_correlations()
        
        # Update prediction accuracy if we made a prediction
        await self._update_prediction_accuracy(timestamp, value)

    async def _update_feature_correlations(self) -> None:
        """Update correlation analysis for features"""
        for window in self.windows.values():
            if len(window.data_points) < self.config['min_data_points']:
                continue
                
            values = np.array([point.value for point in window.data_points])
            
            for feature in window.data_points[0].features.keys():
                feature_values = np.array([
                    point.features[feature]
                    for point in window.data_points
                ])
                
                correlation, _ = stats.pearsonr(values, feature_values)
                self.feature_correlations[feature] = correlation

    async def _update_prediction_accuracy(
        self,
        timestamp: datetime,
        actual_value: float
    ) -> None:
        """Update prediction accuracy metrics"""
        for key, (predicted_value, prediction_time) in self.last_predictions.items():
            if timestamp == prediction_time:
                error = abs(actual_value - predicted_value) / actual_value
                self.prediction_errors.append(error)
                if len(self.prediction_errors) > 1000:
                    self.prediction_errors.pop(0)

    @handle_exceptions
    async def predict_demand(
        self,
        target_time: datetime,
        features: Dict[str, float]
    ) -> Dict[str, Any]:
        """Predict demand for target time"""
        if not all(len(window.data_points) >= self.config['min_data_points']
                  for window in self.windows.values()):
            raise CustomException(
                "PREDICT_001",
                "Insufficient historical data"
            )
            
        # Calculate base prediction using recent trends
        base_prediction = await self._calculate_base_prediction()
        
        # Apply seasonal adjustments
        seasonal_factors = await self._calculate_seasonal_factors(target_time)
        
        # Apply feature adjustments
        feature_adjustments = await self._calculate_feature_adjustments(features)
        
        # Combine predictions
        final_prediction = base_prediction * seasonal_factors * feature_adjustments
        
        # Calculate confidence interval
        confidence_interval = await self._calculate_confidence_interval(
            final_prediction
        )
        
        # Store prediction for accuracy tracking
        prediction_key = target_time.strftime('%Y-%m-%d-%H')
        self.last_predictions[prediction_key] = (final_prediction, target_time)
        
        return {
            'prediction': final_prediction,
            'confidence_interval': confidence_interval,
            'components': {
                'base': base_prediction,
                'seasonal': seasonal_factors,
                'features': feature_adjustments
            },
            'confidence_score': await self._calculate_confidence_score(
                target_time,
                final_prediction
            )
        }

    async def _calculate_base_prediction(self) -> float:
        """Calculate base prediction from recent trends"""
        # Use hour window for short-term trend
        hour_values = self.windows['hour'].get_values()
        if not hour_values:
            return 0.0
            
        # Calculate trend
        x = np.arange(len(hour_values))
        slope, intercept, _, _, _ = stats.linregress(x, hour_values)
        
        # Project trend forward
        next_value = slope * (len(hour_values) + 1) + intercept
        return max(0.0, float(next_value))

    async def _calculate_seasonal_factors(
        self,
        target_time: datetime
    ) -> float:
        """Calculate seasonal adjustment factors"""
        factors = []
        
        for pattern_name, pattern in self.patterns.items():
            pattern_values = pattern.get_pattern()
            if pattern_values:
                bucket = pattern._get_bucket(target_time)
                if bucket in pattern_values:
                    factors.append(pattern_values[bucket])
                    
        return statistics.mean(factors) if factors else 1.0

    async def _calculate_feature_adjustments(
        self,
        features: Dict[str, float]
    ) -> float:
        """Calculate adjustments based on feature correlations"""
        if not self.feature_correlations:
            return 1.0
            
        adjustments = []
        for feature, value in features.items():
            if feature in self.feature_correlations:
                correlation = self.feature_correlations[feature]
                if abs(correlation) > self.config['seasonality_threshold']:
                    adjustments.append(1.0 + (correlation * value))
                    
        return statistics.mean(adjustments) if adjustments else 1.0

    async def _calculate_confidence_interval(
        self,
        prediction: float,
        confidence: float = 0.95
    ) -> Tuple[float, float]:
        """Calculate confidence interval for prediction"""
        if not self.prediction_errors:
            return (prediction * 0.5, prediction * 1.5)
            
        std_dev = statistics.stdev(self.prediction_errors)
        z_score = stats.norm.ppf((1 + confidence) / 2)
        margin = prediction * std_dev * z_score
        
        return (max(0, prediction - margin), prediction + margin)

    async def _calculate_confidence_score(
        self,
        target_time: datetime,
        prediction: float
    ) -> float:
        """Calculate confidence score for prediction"""
        factors = []
        
        # Data quantity factor
        min_points = min(len(window.data_points)
                        for window in self.windows.values())
        data_factor = min(1.0, min_points / self.config['min_data_points'])
        factors.append(data_factor)
        
        # Prediction error factor
        if self.prediction_errors:
            error_factor = 1.0 - statistics.mean(self.prediction_errors)
            factors.append(error_factor)
        
        # Time distance factor
        hours_ahead = (target_time - datetime.utcnow()).total_seconds() / 3600
        time_factor = max(0.0, 1.0 - (hours_ahead / self.config['max_forecast_hours']))
        factors.append(time_factor)
        
        # Seasonal strength factor
        seasonal_strength = await self._calculate_seasonal_strength()
        factors.append(seasonal_strength)
        
        return statistics.mean(factors)

    async def _calculate_seasonal_strength(self) -> float:
        """Calculate strength of seasonal patterns"""
        strengths = []
        
        for pattern in self.patterns.values():
            pattern_values = pattern.get_pattern()
            if pattern_values:
                values = list(pattern_values.values())
                if len(values) >= 2:
                    variation = statistics.stdev(values) / statistics.mean(values)
                    strengths.append(min(1.0, variation / self.config['seasonality_threshold']))
                    
        return statistics.mean(strengths) if strengths else 0.0

    @handle_exceptions
    async def get_forecast(
        self,
        hours_ahead: int,
        features: Optional[Dict[str, Dict[str, float]]] = None
    ) -> List[Dict[str, Any]]:
        """Generate demand forecast for future hours"""
        if hours_ahead > self.config['max_forecast_hours']:
            raise CustomException(
                "PREDICT_002",
                "Forecast period too long",
                {"max_hours": self.config['max_forecast_hours']}
            )
            
        forecast = []
        current_time = datetime.utcnow()
        
        for hour in range(hours_ahead):
            target_time = current_time + timedelta(hours=hour)
            hour_features = features.get(str(hour), {}) if features else {}
            
            prediction = await self.predict_demand(
                target_time,
                hour_features
            )
            
            forecast.append({
                'timestamp': target_time.isoformat(),
                'demand': prediction['prediction'],
                'confidence_interval': prediction['confidence_interval'],
                'confidence_score': prediction['confidence_score']
            })
            
        return forecast

    @handle_exceptions
    async def get_pattern_analysis(self) -> Dict[str, Any]:
        """Get analysis of identified patterns"""
        return {
            pattern_name: {
                'values': pattern.get_pattern(),
                'strength': await self._calculate_seasonal_strength()
            }
            for pattern_name, pattern in self.patterns.items()
        }

    def __str__(self) -> str:
        return f"DemandPredictor(patterns={len(self.patterns)})"

    def __repr__(self) -> str:
        return (f"DemandPredictor(windows={list(self.windows.keys())}, "
                f"patterns={list(self.patterns.keys())})")
