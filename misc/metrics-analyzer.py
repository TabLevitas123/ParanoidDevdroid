# tests/performance/metrics_analyzer.py

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from scipy import stats
from datetime import datetime
import json
from pathlib import Path
import pandas as pd
from collections import defaultdict

from utils.logger import CustomLogger
from tests.performance.metrics_collector import MetricsCollector, MetricSummary

logger = CustomLogger("metrics_analyzer", "analysis.log")

@dataclass
class Trend:
    """Trend analysis results"""
    slope: float
    r_squared: float
    trend_type: str  # 'increasing', 'decreasing', or 'stable'
    confidence: float
    seasonality: Optional[float] = None

@dataclass
class Anomaly:
    """Detected anomaly information"""
    timestamp: float
    metric_value: float
    expected_value: float
    deviation: float
    severity: str  # 'low', 'medium', or 'high'

@dataclass
class Correlation:
    """Correlation between metrics"""
    metric1: str
    metric2: str
    correlation: float
    p_value: float
    relationship: str  # 'strong_positive', 'weak_positive', 'none', 'weak_negative', 'strong_negative'

class MetricsAnalyzer:
    """Analyzes collected metrics for patterns and anomalies"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.collector = metrics_collector
        
        # Analysis settings
        self.trend_threshold = 0.05  # Minimum slope for trend detection
        self.correlation_threshold = 0.5  # Minimum correlation coefficient
        self.anomaly_zscore_threshold = 3.0  # Z-score for anomaly detection
        self.seasonality_threshold = 0.3  # Minimum seasonality strength
        
        # Analysis results
        self.trends: Dict[str, Dict[str, Trend]] = defaultdict(dict)
        self.anomalies: Dict[str, Dict[str, List[Anomaly]]] = defaultdict(lambda: defaultdict(list))
        self.correlations: List[Correlation] = []

    def analyze_trends(
        self,
        category: str,
        name: str,
        window_size: Optional[int] = None
    ) -> Optional[Trend]:
        """Analyze metric for trends"""
        timeseries = self.collector.get_metric_timeseries(category, name)
        if not timeseries or len(timeseries.values) < 2:
            return None
            
        # Convert to numpy arrays
        times = np.array(timeseries.timestamps)
        values = np.array(timeseries.values)
        
        # Normalize time to start from 0
        times = times - times[0]
        
        # If window specified, use only recent data
        if window_size:
            times = times[-window_size:]
            values = values[-window_size:]
        
        try:
            # Calculate trend
            slope, intercept, r_value, p_value, std_err = stats.linregress(times, values)
            r_squared = r_value ** 2
            
            # Determine trend type
            if abs(slope) < self.trend_threshold:
                trend_type = 'stable'
            else:
                trend_type = 'increasing' if slope > 0 else 'decreasing'
            
            # Calculate confidence based on R-squared and sample size
            confidence = r_squared * (1 - 1/len(values))
            
            # Check for seasonality if enough data points
            seasonality = None
            if len(values) >= 24:  # At least 24 data points
                seasonality = self._detect_seasonality(values)
            
            trend = Trend(
                slope=slope,
                r_squared=r_squared,
                trend_type=trend_type,
                confidence=confidence,
                seasonality=seasonality
            )
            
            self.trends[category][name] = trend
            return trend
            
        except Exception as e:
            logger.error(f"Error analyzing trends for {category}.{name}: {str(e)}")
            return None

    def detect_anomalies(
        self,
        category: str,
        name: str,
        method: str = 'zscore'
    ) -> List[Anomaly]:
        """Detect anomalies in metric"""
        timeseries = self.collector.get_metric_timeseries(category, name)
        if not timeseries or len(timeseries.values) < 2:
            return []
            
        values = np.array(timeseries.values)
        timestamps = np.array(timeseries.timestamps)
        
        anomalies = []
        
        if method == 'zscore':
            # Z-score method
            mean = np.mean(values)
            std = np.std(values)
            
            if std == 0:
                return []
                
            zscores = (values - mean) / std
            
            for i, zscore in enumerate(zscores):
                if abs(zscore) >= self.anomaly_zscore_threshold:
                    severity = self._get_anomaly_severity(abs(zscore))
                    anomalies.append(Anomaly(
                        timestamp=timestamps[i],
                        metric_value=values[i],
                        expected_value=mean,
                        deviation=zscore,
                        severity=severity
                    ))
                    
        elif method == 'iqr':
            # Interquartile range method
            q1 = np.percentile(values, 25)
            q3 = np.percentile(values, 75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            
            for i, value in enumerate(values):
                if value < lower or value > upper:
                    deviation = (value - np.median(values)) / iqr
                    severity = self._get_anomaly_severity(abs(deviation))
                    anomalies.append(Anomaly(
                        timestamp=timestamps[i],
                        metric_value=value,
                        expected_value=np.median(values),
                        deviation=deviation,
                        severity=severity
                    ))
        
        self.anomalies[category][name] = anomalies
        return anomalies

    def analyze_correlations(
        self,
        categories: Optional[List[str]] = None
    ) -> List[Correlation]:
        """Analyze correlations between metrics"""
        self.correlations.clear()
        
        # Get all metrics if categories not specified
        if not categories:
            categories = list(self.collector.raw_metrics.keys())
        
        # Collect all metric time series
        all_metrics = []
        for category in categories:
            for name in self.collector.raw_metrics[category]:
                timeseries = self.collector.get_metric_timeseries(category, name)
                if timeseries:
                    all_metrics.append((f"{category}.{name}", timeseries))
        
        # Calculate correlations
        for i, (metric1_name, metric1_data) in enumerate(all_metrics):
            for metric2_name, metric2_data in all_metrics[i+1:]:
                # Align timestamps
                df = pd.DataFrame({
                    'time': metric1_data.timestamps + metric2_data.timestamps,
                    'metric1': metric1_data.values + [None] * len(metric2_data.values),
                    'metric2': [None] * len(metric1_data.values) + metric2_data.values
                })
                df = df.sort_values('time').interpolate()
                
                # Calculate correlation
                correlation, p_value = stats.pearsonr(
                    df['metric1'].values,
                    df['metric2'].values
                )
                
                relationship = self._get_correlation_type(correlation)
                
                if abs(correlation) >= self.correlation_threshold:
                    self.correlations.append(Correlation(
                        metric1=metric1_name,
                        metric2=metric2_name,
                        correlation=correlation,
                        p_value=p_value,
                        relationship=relationship
                    ))
        
        return self.correlations

    def _detect_seasonality(self, values: np.ndarray) -> float:
        """Detect seasonality in time series"""
        # Calculate autocorrelation
        acf = np.correlate(values, values, mode='full') / len(values)
        acf = acf[len(acf)//2:]  # Take only positive lags
        
        # Find peaks in autocorrelation
        peaks = []
        for i in range(1, len(acf)-1):
            if acf[i] > acf[i-1] and acf[i] > acf[i+1]:
                peaks.append((i, acf[i]))
        
        if not peaks:
            return 0.0
        
        # Calculate seasonality strength
        max_peak = max(peaks, key=lambda x: x[1])
        return max_peak[1]

    def _get_anomaly_severity(self, deviation: float) -> str:
        """Determine anomaly severity based on deviation"""
        if deviation >= 5.0:
            return 'high'
        elif deviation >= 4.0:
            return 'medium'
        else:
            return 'low'

    def _get_correlation_type(self, correlation: float) -> str:
        """Determine correlation relationship type"""
        if correlation >= 0.8:
            return 'strong_positive'
        elif correlation >= 0.5:
            return 'weak_positive'
        elif correlation <= -0.8:
            return 'strong_negative'
        elif correlation <= -0.5:
            return 'weak_negative'
        else:
            return 'none'

    def save_analysis(self, filepath: str):
        """Save analysis results to file"""
        analysis_data = {
            'trends': {
                category: {
                    name: trend.__dict__
                    for name, trend in trends.items()
                }
                for category, trends in self.trends.items()
            },
            'anomalies': {
                category: {
                    name: [anomaly.__dict__ for anomaly in anomalies]
                    for name, anomalies in cat_anomalies.items()
                }
                for category, cat_anomalies in self.anomalies.items()
            },
            'correlations': [
                correlation.__dict__
                for correlation in self.correlations
            ]
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(analysis_data, f, indent=2)
        
        logger.info(f"Analysis results saved to {filepath}")

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive analysis report"""
        return {
            'summary': {
                'total_metrics': sum(
                    len(metrics) for metrics in self.collector.raw_metrics.values()
                ),
                'total_anomalies': sum(
                    len(anomalies)
                    for cat_anomalies in self.anomalies.values()
                    for anomalies in cat_anomalies.values()
                ),
                'total_correlations': len(self.correlations),
                'metrics_by_category': {
                    category: len(metrics)
                    for category, metrics in self.collector.raw_metrics.items()
                }
            },
            'key_findings': {
                'significant_trends': [
                    {
                        'metric': f"{category}.{name}",
                        'trend': trend.__dict__
                    }
                    for category, trends in self.trends.items()
                    for name, trend in trends.items()
                    if trend.confidence >= 0.8
                ],
                'strong_correlations': [
                    correlation.__dict__
                    for correlation in self.correlations
                    if abs(correlation.correlation) >= 0.8
                ],
                'severe_anomalies': [
                    {
                        'metric': f"{category}.{name}",
                        'anomaly': anomaly.__dict__
                    }
                    for category, cat_anomalies in self.anomalies.items()
                    for name, anomalies in cat_anomalies.items()
                    for anomaly in anomalies
                    if anomaly.severity == 'high'
                ]
            },
            'recommendations': self._generate_recommendations()
        }

    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        # Check for performance degradation
        for category, trends in self.trends.items():
            for name, trend in trends.items():
                if (trend.trend_type == 'increasing' and 
                    'response_time' in name.lower() and 
                    trend.confidence >= 0.7):
                    recommendations.append({
                        'type': 'performance',
                        'severity': 'high',
                        'message': f"Performance degradation detected in {category}.{name}. "
                                 f"Investigation recommended."
                    })
        
        # Check for resource issues
        for category, cat_anomalies in self.anomalies.items():
            for name, anomalies in cat_anomalies.items():
                high_anomalies = [a for a in anomalies if a.severity == 'high']
                if len(high_anomalies) >= 3:
                    recommendations.append({
                        'type': 'resource',
                        'severity': 'medium',
                        'message': f"Multiple severe anomalies detected in {category}.{name}. "
                                 f"Resource scaling may be needed."
                    })
        
        # Check for correlated issues
        for correlation in self.correlations:
            if (correlation.relationship == 'strong_positive' and 
                'error' in correlation.metric1.lower() and 
                'resource' in correlation.metric2.lower()):
                recommendations.append({
                    'type': 'correlation',
                    'severity': 'high',
                    'message': f"Strong correlation detected between errors and resource usage "
                             f"({correlation.metric1} and {correlation.metric2}). "
                             f"Resource constraints may be causing errors."
                })
        
        return recommendations

if __name__ == "__main__":
    # Test analysis
    collector = MetricsCollector()
    
    # Add some test data
    timestamps = list(range(100))
    values = [np.sin(t/10) + np.random.normal(0, 0.1) for t in timestamps]
    
    for t, v in zip(timestamps, values):
        collector.add_metric("test", "metric1", v, t)
    
    # Run analysis
    analyzer = MetricsAnalyzer(collector)
    analyzer.analyze_trends("test", "metric1")
    analyzer.detect_anomalies("test", "metric1")
    
    # Save results
    analyzer.save_analysis("test/reports/test_analysis.json")
    print("Test analysis completed")
