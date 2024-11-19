import heapq
import logging
from typing import Any, List, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskPriorityManager:
    """Class for managing task priorities using a priority queue."""
    def __init__(self):
        self.task_queue: List[Tuple[int, Any]] = []
        logger.info("Task Priority Manager initialized.")

    def add_task(self, priority: int, task: Any):
        """Add a task to the priority queue."""
        heapq.heappush(self.task_queue, (priority, task))
        logger.info(f"Task added with priority {priority}: {task}")

    def get_next_task(self) -> Any:
        """Retrieve and remove the highest-priority task."""
        if not self.task_queue:
            logger.warning("No tasks in the queue.")
            return None
        priority, task = heapq.heappop(self.task_queue)
        logger.info(f"Retrieved task with priority {priority}: {task}")
        return task

    def peek_next_task(self) -> Any:
        """Peek at the highest-priority task without removing it."""
        if not self.task_queue:
            logger.warning("No tasks in the queue.")
            return None
        priority, task = self.task_queue[0]
        logger.info(f"Peeked at task with priority {priority}: {task}")
        return task

if __name__ == '__main__':
    priority_manager = TaskPriorityManager()
    priority_manager.add_task(3, "Task C")
    priority_manager.add_task(1, "Task A")
    priority_manager.add_task(2, "Task B")
    print("Next Task:", priority_manager.get_next_task())
    print("Peek Task:", priority_manager.peek_next_task())
    print("Next Task:", priority_manager.get_next_task())
