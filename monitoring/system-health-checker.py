import psutil
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemHealthChecker:
    """Class for checking system health metrics."""
    @staticmethod
    def check_cpu_usage(threshold: float = 90.0):
        """Check if CPU usage exceeds the threshold."""
        usage = psutil.cpu_percent()
        if usage > threshold:
            logger.warning(f"High CPU usage detected: {usage}%")
        else:
            logger.info(f"CPU usage is normal: {usage}%")
        return usage

    @staticmethod
    def check_memory_usage(threshold: float = 80.0):
        """Check if memory usage exceeds the threshold."""
        memory = psutil.virtual_memory()
        if memory.percent > threshold:
            logger.warning(f"High memory usage detected: {memory.percent}%")
        else:
            logger.info(f"Memory usage is normal: {memory.percent}%")
        return memory.percent

if __name__ == '__main__':
    cpu_usage = SystemHealthChecker.check_cpu_usage()
    memory_usage = SystemHealthChecker.check_memory_usage()
    print(f"CPU Usage: {cpu_usage}%")
    print(f"Memory Usage: {memory_usage}%")
