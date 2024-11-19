import threading
import time
import logging
from typing import Callable, Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskScheduler:
    """Class for scheduling and executing tasks."""
    def __init__(self):
        self.tasks: Dict[str, threading.Timer] = {}
        logger.info("Task Scheduler initialized.")

    def add_task(self, task_id: str, interval: int, function: Callable, *args, **kwargs):
        """Add a task to the scheduler."""
        if task_id in self.tasks:
            logger.warning(f"Task {task_id} already exists.")
            return
        timer = threading.Timer(interval, function, args=args, kwargs=kwargs)
        self.tasks[task_id] = timer
        timer.start()
        logger.info(f"Task {task_id} scheduled to run every {interval} seconds.")

    def cancel_task(self, task_id: str):
        """Cancel a scheduled task."""
        if task_id not in self.tasks:
            logger.warning(f"Task {task_id} does not exist.")
            return
        timer = self.tasks.pop(task_id)
        timer.cancel()
        logger.info(f"Task {task_id} cancelled.")

    def clear_all_tasks(self):
        """Cancel all scheduled tasks."""
        for task_id, timer in self.tasks.items():
            timer.cancel()
        self.tasks.clear()
        logger.info("All tasks cleared.")

if __name__ == '__main__':
    scheduler = TaskScheduler()

    def sample_task(message):
        logger.info(f"Task executed: {message}")

    scheduler.add_task("task1", 2, sample_task, "Hello, world!")
    time.sleep(5)
    scheduler.cancel_task("task1")
    scheduler.clear_all_tasks()
