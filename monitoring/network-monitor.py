import psutil
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkMonitor:
    """Class for monitoring network usage."""
    @staticmethod
    def monitor_network():
        """Log network statistics."""
        stats = psutil.net_io_counters()
        logger.info(f"Bytes Sent: {stats.bytes_sent}")
        logger.info(f"Bytes Received: {stats.bytes_recv}")
        return stats.bytes_sent, stats.bytes_recv

if __name__ == '__main__':
    bytes_sent, bytes_recv = NetworkMonitor.monitor_network()
    print(f"Bytes Sent: {bytes_sent}")
    print(f"Bytes Received: {bytes_recv}")
