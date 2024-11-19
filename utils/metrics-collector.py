import psutil
import logging
from typing import Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetricsCollector:
    """Class for collecting system performance metrics."""
    @staticmethod
    def collect_cpu_metrics() -> Dict[str, float]:
        """Collect CPU usage metrics."""
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count(logical=True)
        metrics = {
            'cpu_percent': cpu_percent,
            'cpu_count': cpu_count
        }
        logger.info(f"CPU Metrics: {metrics}")
        return metrics

    @staticmethod
    def collect_memory_metrics() -> Dict[str, float]:
        """Collect memory usage metrics."""
        mem = psutil.virtual_memory()
        metrics = {
            'total_memory_gb': mem.total / (1024 ** 3),
            'used_memory_gb': mem.used / (1024 ** 3),
            'memory_percent': mem.percent
        }
        logger.info(f"Memory Metrics: {metrics}")
        return metrics

    @staticmethod
    def collect_disk_metrics() -> Dict[str, float]:
        """Collect disk usage metrics."""
        disk = psutil.disk_usage('/')
        metrics = {
            'total_disk_gb': disk.total / (1024 ** 3),
            'used_disk_gb': disk.used / (1024 ** 3),
            'disk_percent': disk.percent
        }
        logger.info(f"Disk Metrics: {metrics}")
        return metrics

if __name__ == '__main__':
    collector = MetricsCollector()
    cpu_metrics = collector.collect_cpu_metrics()
    memory_metrics = collector.collect_memory_metrics()
    disk_metrics = collector.collect_disk_metrics()
    print("CPU Metrics:", cpu_metrics)
    print("Memory Metrics:", memory_metrics)
    print("Disk Metrics:", disk_metrics)
