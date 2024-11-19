# tests/performance/resource_monitor.py

import asyncio
import time
from datetime import datetime, timedelta
import psutil
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json
from pathlib import Path
import numpy as np

from utils.logger import CustomLogger

logger = CustomLogger("resource_monitor", "resources.log")

@dataclass
class ResourceMetrics:
    """Container for system resource metrics"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used: int  # bytes
    memory_available: int  # bytes
    swap_percent: float
    disk_usage_percent: float
    disk_read_bytes: int
    disk_write_bytes: int
    network_sent_bytes: int
    network_recv_bytes: int
    io_wait: float
    load_average: Tuple[float, float, float]
    process_count: int
    thread_count: int
    handle_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            'timestamp': self.timestamp,
            'cpu': {
                'percent': self.cpu_percent,
                'io_wait': self.io_wait,
                'load_average': list(self.load_average)
            },
            'memory': {
                'percent': self.memory_percent,
                'used': self.memory_used,
                'available': self.memory_available,
                'swap_percent': self.swap_percent
            },
            'disk': {
                'usage_percent': self.disk_usage_percent,
                'read_bytes': self.disk_read_bytes,
                'write_bytes': self.disk_write_bytes
            },
            'network': {
                'sent_bytes': self.network_sent_bytes,
                'recv_bytes': self.network_recv_bytes
            },
            'processes': {
                'count': self.process_count,
                'threads': self.thread_count,
                'handles': self.handle_count
            }
        }

class ResourceMonitor:
    """Monitors and tracks system resource usage"""
    
    def __init__(
        self,
        sampling_interval: float = 1.0,
        history_size: int = 3600  # 1 hour at 1 second intervals
    ):
        self.sampling_interval = sampling_interval
        self.history_size = history_size
        self.metrics_history: List[ResourceMetrics] = []
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Previous readings for calculating deltas
        self.prev_disk_io = psutil.disk_io_counters()
        self.prev_net_io = psutil.net_io_counters()
        self.start_time = None
        
        # Alert thresholds
        self.thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_percent': 90.0,
            'swap_percent': 60.0,
            'io_wait': 30.0
        }
        
        # Anomaly detection
        self.baseline_metrics: Optional[Dict[str, float]] = None
        self.std_devs: Optional[Dict[str, float]] = None

    async def start_monitoring(self):
        """Start resource monitoring"""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        self.start_time = datetime.now()
        self.monitoring_task = asyncio.create_task(self._monitor_resources())
        logger.info("Resource monitoring started")

    async def stop_monitoring(self):
        """Stop resource monitoring"""
        if not self.is_monitoring:
            return
            
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Resource monitoring stopped")

    async def _monitor_resources(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                metrics = await self._collect_metrics()
                self.metrics_history.append(metrics)
                
                # Trim history if needed
                if len(self.metrics_history) > self.history_size:
                    self.metrics_history = self.metrics_history[-self.history_size:]
                
                # Check for alerts
                await self._check_alerts(metrics)
                
                # Detect anomalies
                await self._detect_anomalies(metrics)
                
                await asyncio.sleep(self.sampling_interval)
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {str(e)}")
                await asyncio.sleep(self.sampling_interval)

    async def _collect_metrics(self) -> ResourceMetrics:
        """Collect current system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            cpu_times = psutil.cpu_times_percent()
            load_avg = psutil.getloadavg()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            disk_read_delta = disk_io.read_bytes - self.prev_disk_io.read_bytes
            disk_write_delta = disk_io.write_bytes - self.prev_disk_io.write_bytes
            self.prev_disk_io = disk_io
            
            # Network metrics
            net_io = psutil.net_io_counters()
            net_sent_delta = net_io.bytes_sent - self.prev_net_io.bytes_sent
            net_recv_delta = net_io.bytes_recv - self.prev_net_io.bytes_recv
            self.prev_net_io = net_io
            
            # Process metrics
            process_count = len(psutil.pids())
            thread_count = sum(p.num_threads() for p in psutil.process_iter(['num_threads']))
            handle_count = sum(p.num_handles() for p in psutil.process_iter(['num_handles']))
            
            return ResourceMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used=memory.used,
                memory_available=memory.available,
                swap_percent=swap.percent,
                disk_usage_percent=disk.percent,
                disk_read_bytes=disk_read_delta,
                disk_write_bytes=disk_write_delta,
                network_sent_bytes=net_sent_delta,
                network_recv_bytes=net_recv_delta,
                io_wait=cpu_times.iowait,
                load_average=load_avg,
                process_count=process_count,
                thread_count=thread_count,
                handle_count=handle_count
            )
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
            raise

    async def _check_alerts(self, metrics: ResourceMetrics):
        """Check metrics against thresholds for alerts"""
        alerts = []
        
        if metrics.cpu_percent > self.thresholds['cpu_percent']:
            alerts.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")
            
        if metrics.memory_percent > self.thresholds['memory_percent']:
            alerts.append(f"High memory usage: {metrics.memory_percent:.1f}%")
            
        if metrics.disk_usage_percent > self.thresholds['disk_percent']:
            alerts.append(f"High disk usage: {metrics.disk_usage_percent:.1f}%")
            
        if metrics.swap_percent > self.thresholds['swap_percent']:
            alerts.append(f"High swap usage: {metrics.swap_percent:.1f}%")
            
        if metrics.io_wait > self.thresholds['io_wait']:
            alerts.append(f"High I/O wait: {metrics.io_wait:.1f}%")
        
        if alerts:
            logger.warning("Resource alerts: " + "; ".join(alerts))

    async def _detect_anomalies(self, metrics: ResourceMetrics):
        """Detect anomalous behavior in metrics"""
        # Calculate baseline if needed
        if not self.baseline_metrics and len(self.metrics_history) >= 60:
            await self._calculate_baseline()
        
        if self.baseline_metrics and self.std_devs:
            anomalies = []
            
            # Check each metric for anomalies
            for metric_name, baseline in self.baseline_metrics.items():
                current_value = getattr(metrics, metric_name)
                std_dev = self.std_devs[metric_name]
                
                # Consider values more than 3 standard deviations from baseline as anomalies
                if abs(current_value - baseline) > (3 * std_dev):
                    anomalies.append(
                        f"{metric_name}: {current_value:.1f} "
                        f"(baseline: {baseline:.1f} ± {std_dev:.1f})"
                    )
            
            if anomalies:
                logger.warning("Anomalies detected: " + "; ".join(anomalies))

    async def _calculate_baseline(self):
        """Calculate baseline metrics and standard deviations"""
        metric_names = [
            'cpu_percent', 'memory_percent', 'disk_usage_percent',
            'io_wait', 'process_count', 'thread_count'
        ]
        
        self.baseline_metrics = {}
        self.std_devs = {}
        
        for metric_name in metric_names:
            values = [getattr(m, metric_name) for m in self.metrics_history]
            self.baseline_metrics[metric_name] = np.mean(values)
            self.std_devs[metric_name] = np.std(values)

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of collected metrics"""
        if not self.metrics_history:
            return {}
        
        metrics_array = np.array([
            [m.cpu_percent, m.memory_percent, m.disk_usage_percent]
            for m in self.metrics_history
        ])
        
        return {
            'duration': str(datetime.now() - self.start_time),
            'samples': len(self.metrics_history),
            'cpu': {
                'min': float(np.min(metrics_array[:, 0])),
                'max': float(np.max(metrics_array[:, 0])),
                'mean': float(np.mean(metrics_array[:, 0])),
                'std': float(np.std(metrics_array[:, 0]))
            },
            'memory': {
                'min': float(np.min(metrics_array[:, 1])),
                'max': float(np.max(metrics_array[:, 1])),
                'mean': float(np.mean(metrics_array[:, 1])),
                'std': float(np.std(metrics_array[:, 1]))
            },
            'disk': {
                'min': float(np.min(metrics_array[:, 2])),
                'max': float(np.max(metrics_array[:, 2])),
                'mean': float(np.mean(metrics_array[:, 2])),
                'std': float(np.std(metrics_array[:, 2]))
            }
        }

    async def save_metrics(self, filepath: str):
        """Save collected metrics to file"""
        metrics_data = {
            'summary': self.get_metrics_summary(),
            'metrics': [m.to_dict() for m in self.metrics_history]
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        
        logger.info(f"Metrics saved to {filepath}")

async def main():
    """Run resource monitor as standalone"""
    monitor = ResourceMonitor()
    
    try:
        await monitor.start_monitoring()
        
        # Monitor for 1 hour
        await asyncio.sleep(3600)
        
        # Save results
        await monitor.save_metrics('test/reports/resource_metrics.json')
        
    finally:
        await monitor.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
