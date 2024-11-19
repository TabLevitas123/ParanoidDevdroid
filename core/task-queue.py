import heapq
import logging
from typing import Any, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskQueue:
    """Class for managing a priority-based task queue."""
    def __init__(self):
        self.queue = []
        self.counter = 0  # Unique counter to maintain task order
        logger.info("Task Queue initialized.")

    def add_task(self, priority: int, task: Any):
        """Add a task with a specific priority."""
        heapq.heappush(self.queue, (priority, self.counter, task))
        self.counter += 1
        logger.info(f"Task added: {task} with priority {priority}")

    def get_task(self) -> Any:
        """Retrieve the highest priority task."""
        if not self.queue:
            logger.warning("Task queue is empty.")
            return None
        task = heapq.heappop(self.queue)[-1]
        logger.info(f"Task retrieved: {task}")
        return task

if __name__ == '__main__':
    queue = TaskQueue()
    queue.add_task(3, "Low priority task")
    queue.add_task(1, "High priority task")
    queue.add_task(2, "Medium priority task")
    print("Next Task:", queue.get_task())
    print("Next Task:", queue.get_task())
    print("Next Task:", queue.get_task())
