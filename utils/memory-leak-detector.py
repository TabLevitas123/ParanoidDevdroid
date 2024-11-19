import gc
import tracemalloc
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemoryLeakDetector:
    """Class to detect memory leaks in an application."""
    def __init__(self):
        tracemalloc.start()
        self.snapshots = []

    def take_snapshot(self):
        """Take a memory snapshot and log it."""
        snapshot = tracemalloc.take_snapshot()
        self.snapshots.append(snapshot)
        logger.info(f"Snapshot taken: {len(self.snapshots)} total snapshots.")

    def compare_snapshots(self):
        """Compare the latest two snapshots and return memory usage statistics."""
        if len(self.snapshots) < 2:
            logger.warning("Not enough snapshots to compare.")
            return {}
        stats = self.snapshots[-1].compare_to(self.snapshots[-2], 'lineno')
        leaks = {
            'total_leaked_kb': sum(stat.size_diff for stat in stats) / 1024,
            'largest_leak_kb': max(stat.size_diff for stat in stats) / 1024 if stats else 0
        }
        logger.info(f"Memory Leak Detected: {leaks}")
        return leaks

    def stop(self):
        """Stop tracemalloc and clean up."""
        tracemalloc.stop()
        logger.info("Memory leak detection stopped.")

if __name__ == '__main__':
    detector = MemoryLeakDetector()
    detector.take_snapshot()
    # Simulate memory usage
    _temp = [b'a' * 1024 for _ in range(10000)]
    del _temp
    gc.collect()
    detector.take_snapshot()
    leaks = detector.compare_snapshots()
    print(f"Memory Leak Results: {leaks}")
    detector.stop()
