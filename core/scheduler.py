import threading
import time
import logging
from typing import Callable

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Scheduler:
    """Class for scheduling and running periodic tasks."""
    def __init__(self):
        self.tasks = []
        logger.info("Scheduler initialized.")

    def add_task(self, task: Callable, interval: int):
        """Add a task to be run periodically."""
        self.tasks.append((task, interval))
        logger.info(f"Task {task.__name__} added with interval {interval} seconds.")

    def start(self):
        """Start the scheduler."""
        def run_task(task: Callable, interval: int):
            while True:
                logger.info(f"Running task: {task.__name__}")
                task()
                time.sleep(interval)
        for task, interval in self.tasks:
            thread = threading.Thread(target=run_task, args=(task, interval), daemon=True)
            thread.start()
        logger.info("Scheduler started.")

if __name__ == '__main__':
    scheduler = Scheduler()

    def sample_task():
        logger.info("Sample task executed.")

    scheduler.add_task(sample_task, 2)
    scheduler.start()
    time.sleep(10)
