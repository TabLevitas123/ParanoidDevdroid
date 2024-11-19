import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EventLogger:
    """Class for logging application events."""
    @staticmethod
    def log_event(event_name: str, details: str = ""):
        """Log an event with its details."""
        timestamp = datetime.utcnow().isoformat()
        logger.info(f"[{timestamp}] Event: {event_name} | Details: {details}")

if __name__ == '__main__':
    EventLogger.log_event("Startup", "Application has started.")
    EventLogger.log_event("Shutdown", "Application is shutting down.")
