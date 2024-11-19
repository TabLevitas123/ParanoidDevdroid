import time
import logging
from functools import wraps

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceTracker:
    """Class for tracking application performance."""
    @staticmethod
    def track_time(func):
        """Decorator to track execution time of a function."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            logger.info(f"Function {func.__name__} executed in {end_time - start_time:.2f} seconds.")
            return result
        return wrapper

if __name__ == '__main__':
    @PerformanceTracker.track_time
    def sample_task():
        time.sleep(1)
        logger.info("Sample task completed.")

    sample_task()
