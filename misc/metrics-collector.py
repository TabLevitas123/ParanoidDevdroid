# tests/performance/metrics_collector.py

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import numpy as np
from collections import defaultdict
import json
from pathlib import Path

from utils.logger import CustomLogger

logger = CustomLogger("metrics_collector", "metrics.log")

@dataclass
class MetricSummary:
    """Summary statistics for a metric"""
    min_value: float
    max_value: float
    mean: float
    median: float
    p95: float
    std_dev: float
    sample_count: int

    def to_dict(self) -> Dict[str, float]:
        return {
            'min': self.min_value,
            'max': self.max_value,
            'mean': self.mean,
            'median': self.median,
            'p95': self.p95,
            'std_dev': self.std_dev,
            'samples': self.sample_count
        }

@dataclass
class TimeSeriesMetric:
    """Time series data for a metric"""
    timestamps: List[float]
    values: List[float]
    
    def to_dict(self) -> Dict[str, List[float]]:
        return {
            'timestamps': self.timestamps,
            'values': self.values
        }

class MetricsCollector:
    """Collects and processes test metrics"""
    
    def __init__(self):
        # Raw metrics storage
        self.raw_metrics: Dict[str, Dict[str, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self.timestamps: Dict[str, Dict[str, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        
        # Metric metadata
        self.metric_units: Dict[str, Dict[str, str]] = defaultdict(dict)
        self.metric_descriptions: Dict[str, Dict[str, str]] = defaultdict(dict)
        
        # Initialize standard metrics
        self._initialize_standard_metrics()

    def _initialize_standard_metrics(self):
        """Initialize standard metric definitions"""
        # Response time metrics
        self.add_metric_metadata(
            "response_time", "overall",
            "seconds", "Overall response time"
        )
        self.add_metric_metadata(
            "response_time", "api",
            "seconds", "API endpoint response time"
        )
        
        # Resource metrics
        self.add_metric_metadata(
            "resources", "cpu_usage",
            "percent", "CPU usage percentage"
        )
        self.add_metric_metadata(
            "resources", "memory_usage",
            "bytes", "Memory usage in bytes"
        )
        self.add_metric_metadata(
            "resources", "disk_io",
            "bytes/sec", "Disk I/O rate"
        )
        
        # Workload metrics
        self.add_metric_metadata(
            "workload", "concurrent_users",
            "count", "Number of concurrent users"
        )
        self.add_metric_metadata(
            "workload", "requests_per_second",
            "count/sec", "Request rate"
        )
        self.add_metric_metadata(
            "workload", "error_rate",
            "percent", "Error rate percentage"
        )

    def add_metric_metadata(
        self,
        category: str,
        name: str,
        unit: str,
        description: str
    ):
        """Add metadata for a metric"""
        self.metric_units[category][name] = unit
        self.metric_descriptions[category][name] = description

    def add_metric(
        self,
        category: str,
        name: str,
        value: float,
        timestamp: Optional[float] = None
    ):
        """Add a metric value"""
        if timestamp is None:
            timestamp = datetime.utcnow().timestamp()
            
        self.raw_metrics[category][name].append(value)
        self.timestamps[category][name].append(timestamp)

    def add_metrics_batch(
        self,
        category: str,
        metrics: Dict[str, float],
        timestamp: Optional[float] = None
    ):
        """Add multiple metrics at once"""
        if timestamp is None:
            timestamp = datetime.utcnow().timestamp()
            
        for name, value in metrics.items():
            self.raw_metrics[category][name].append(value)
            self.timestamps[category][name].append(timestamp)

    def get_metric_summary(
        self,
        category: str,
        name: str
    ) -> Optional[MetricSummary]:
        """Get summary statistics for a metric"""
        values = self.raw_metrics[category].get(name)
        if not values:
            return None
            
        values_array = np.array(values)
        return MetricSummary(
            min_value=float(np.min(values_array)),
            max_value=float(np.max(values_array)),
            mean=float(np.mean(values_array)),
            median=float(np.median(values_array)),
            p95=float(np.percentile(values_array, 95)),
            std_dev=float(np.std(values_array)),
            sample_count=len(values)
        )

    def get_metric_timeseries(
        self,
        category: str,
        name: str
    ) -> Optional[TimeSeriesMetric]:
        """Get time series data for a metric"""
        values = self.raw_metrics[category].get(name)
        timestamps = self.timestamps[category].get(name)
        
        if not values or not timestamps:
            return None
            
        return TimeSeriesMetric(
            timestamps=timestamps,
            values=values
        )

    def get_all_summaries(self) -> Dict[str, Dict[str, MetricSummary]]:
        """Get summaries for all metrics"""
        summaries = {}
        for category in self.raw_metrics:
            summaries[category] = {}
            for name in self.raw_metrics[category]:
                summary = self.get_metric_summary(category, name)
                if summary:
                    summaries[category][name] = summary
        return summaries

    def get_all_timeseries(self) -> Dict[str, Dict[str, TimeSeriesMetric]]:
        """Get time series for all metrics"""
        series = {}
        for category in self.raw_metrics:
            series[category] = {}
            for name in self.raw_metrics[category]:
                timeseries = self.get_metric_timeseries(category, name)
                if timeseries:
                    series[category][name] = timeseries
        return series

    def save_metrics(self, filepath: str):
        """Save all metrics to file"""
        data = {
            'metadata': {
                'units': self.metric_units,
                'descriptions': self.metric_descriptions
            },
            'summaries': {
                category: {
                    name: summary.to_dict()
                    for name, summary in summaries.items()
                }
                for category, summaries in self.get_all_summaries().items()
            },
            'timeseries': {
                category: {
                    name: series.to_dict()
                    for name, series in cat_series.items()
                }
                for category, cat_series in self.get_all_timeseries().items()
            }
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Metrics saved to {filepath}")

    def clear_metrics(self):
        """Clear all collected metrics"""
        self.raw_metrics.clear()
        self.timestamps.clear()
        logger.info("Metrics cleared")

if __name__ == "__main__":
    # Simple test
    collector = MetricsCollector()
    
    # Add some test metrics
    for i in range(100):
        collector.add_metrics_batch(
            "test_category",
            {
                "metric1": np.random.normal(100, 10),
                "metric2": np.random.exponential(5)
            }
        )
    
    # Save test metrics
    collector.save_metrics("test/reports/test_metrics.json")
    print("Test metrics saved")
