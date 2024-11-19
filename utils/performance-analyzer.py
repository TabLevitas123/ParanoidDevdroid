import psutil
import time
import logging
from typing import Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    """Class to analyze system performance over a period."""
    def __init__(self, interval: int = 5):
        self.interval = interval

    def analyze_cpu_usage(self) -> Dict[str, float]:
        """Analyze CPU usage during the interval."""
        logger.info(f"Starting CPU analysis for {self.interval} seconds.")
        cpu_percentages = []
        for _ in range(self.interval):
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_percentages.append(cpu_percent)
        avg_cpu = sum(cpu_percentages) / len(cpu_percentages)
        logger.info(f"Average CPU Usage: {avg_cpu}%")
        return {'average_cpu_percent': avg_cpu}

    def analyze_memory_usage(self) -> Dict[str, float]:
        """Analyze memory usage during the interval."""
        mem = psutil.virtual_memory()
        metrics = {
            'total_memory_gb': mem.total / (1024 ** 3),
            'used_memory_gb': mem.used / (1024 ** 3),
            'memory_percent': mem.percent
        }
        logger.info(f"Memory Metrics: {metrics}")
        return metrics

    def analyze_disk_usage(self) -> Dict[str, float]:
        """Analyze disk usage during the interval."""
        disk = psutil.disk_usage('/')
        metrics = {
            'total_disk_gb': disk.total / (1024 ** 3),
            'used_disk_gb': disk.used / (1024 ** 3),
            'disk_percent': disk.percent
        }
        logger.info(f"Disk Metrics: {metrics}")
        return metrics

if __name__ == '__main__':
    analyzer = PerformanceAnalyzer(interval=5)
    cpu_metrics = analyzer.analyze_cpu_usage()
    memory_metrics = analyzer.analyze_memory_usage()
    disk_metrics = analyzer.analyze_disk_usage()
    print("CPU Metrics:", cpu_metrics)
    print("Memory Metrics:", memory_metrics)
    print("Disk Metrics:", disk_metrics)
