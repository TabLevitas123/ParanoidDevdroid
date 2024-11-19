import logging
from typing import Callable, Dict, List

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationHub:
    """Class for managing centralized notifications."""
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        logger.info("Notification Hub initialized.")

    def subscribe(self, event_name: str, callback: Callable):
        """Subscribe to a specific event."""
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        self._subscribers[event_name].append(callback)
        logger.info(f"Subscriber added for event: {event_name}")

    def notify(self, event_name: str, *args, **kwargs):
        """Notify all subscribers of an event."""
        callbacks = self._subscribers.get(event_name, [])
        if not callbacks:
            logger.warning(f"No subscribers for event: {event_name}")
            return
        for callback in callbacks:
            try:
                callback(*args, **kwargs)
                logger.info(f"Notified subscriber for event: {event_name}")
            except Exception as e:
                logger.error(f"Error notifying subscriber: {e}")

if __name__ == '__main__':
    hub = NotificationHub()

    def on_test_event(data):
        logger.info(f"Test event received with data: {data}")

    hub.subscribe("test_event", on_test_event)
    hub.notify("test_event", data="Hello from NotificationHub!")
