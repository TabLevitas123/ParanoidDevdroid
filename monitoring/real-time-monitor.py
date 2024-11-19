import psutil
import time
import logging
from typing import Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealTimeMonitor:
    """Class for real-time system monitoring."""
    def __init__(self, interval: int = 1):
        self.interval = interval
        logger.info(f"Real-Time Monitor initialized with interval {self.interval} seconds.")

    def collect_metrics(self) -> Dict[str, float]:
        """Collect real-time system metrics."""
        cpu_usage = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        metrics = {
            'cpu_percent': cpu_usage,
            'memory_percent': memory.percent,
            'available_memory_gb': memory.available / (1024 ** 3)
        }
        logger.info(f"Collected Metrics: {metrics}")
        return metrics

    def start_monitoring(self, duration: int = 5):
        """Start monitoring in real time for a fixed duration."""
        end_time = time.time() + duration
        try:
            while time.time() < end_time:
                metrics = self.collect_metrics()
                print(metrics)
                time.sleep(self.interval)
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user.")

if __name__ == '__main__':
    monitor = RealTimeMonitor(interval=2)
    monitor.start_monitoring(duration=5)
