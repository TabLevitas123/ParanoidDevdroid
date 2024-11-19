import logging
from typing import Callable, Dict, List

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EventDispatcher:
    """Class for dispatching events to subscribers."""
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        logger.info("Event Dispatcher initialized.")

    def subscribe(self, event_name: str, callback: Callable):
        """Subscribe a callback to an event."""
        if event_name not in self.subscribers:
            self.subscribers[event_name] = []
        self.subscribers[event_name].append(callback)
        logger.info(f"Callback {callback.__name__} subscribed to event {event_name}.")

    def dispatch(self, event_name: str, *args, **kwargs):
        """Dispatch an event to all its subscribers."""
        if event_name in self.subscribers:
            for callback in self.subscribers[event_name]:
                logger.info(f"Dispatching event {event_name} to {callback.__name__}.")
                callback(*args, **kwargs)
        else:
            logger.warning(f"No subscribers for event {event_name}.")

if __name__ == '__main__':
    dispatcher = EventDispatcher()

    def on_user_registered(username):
        logger.info(f"User registered: {username}")

    dispatcher.subscribe("user_registered", on_user_registered)
    dispatcher.dispatch("user_registered", username="test_user")
