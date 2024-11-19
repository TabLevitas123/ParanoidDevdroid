import threading
import logging
from typing import Callable, Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ThreadManager:
    """Class for managing threads."""
    def __init__(self):
        self.threads: Dict[str, threading.Thread] = {}
        logger.info("Thread Manager initialized.")

    def start_thread(self, thread_name: str, target: Callable, *args, **kwargs):
        """Start a new thread."""
        if thread_name in self.threads and self.threads[thread_name].is_alive():
            logger.warning(f"Thread {thread_name} is already running.")
            return
        thread = threading.Thread(target=target, args=args, kwargs=kwargs, name=thread_name)
        self.threads[thread_name] = thread
        thread.start()
        logger.info(f"Thread {thread_name} started.")

    def stop_thread(self, thread_name: str):
        """Stop a thread (unsafe)."""
        thread = self.threads.get(thread_name)
        if not thread:
            logger.warning(f"Thread {thread_name} not found.")
            return
        # Warning: Stopping threads forcefully is unsafe and not recommended.
        logger.warning(f"Cannot safely stop thread {thread_name}. Threading API does not support this.")

    def list_threads(self):
        """List all managed threads."""
        active_threads = [name for name, thread in self.threads.items() if thread.is_alive()]
        logger.info(f"Active Threads: {active_threads}")
        return active_threads

if __name__ == '__main__':
    def sample_task(duration):
        import time
        logger.info("Sample task started.")
        time.sleep(duration)
        logger.info("Sample task completed.")

    thread_manager = ThreadManager()
    thread_manager.start_thread("sample_thread", sample_task, 5)
    thread_manager.list_threads()
