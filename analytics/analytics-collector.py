import logging
from typing import Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalyticsCollector:
    """Class for collecting and summarizing analytics data."""
    def __init__(self):
        self.data: Dict[str, int] = {}
        logger.info("Analytics Collector initialized.")

    def log_event(self, event_name: str):
        """Log an event occurrence."""
        if event_name not in self.data:
            self.data[event_name] = 0
        self.data[event_name] += 1
        logger.info(f"Event {event_name} logged. Total: {self.data[event_name]}")

    def summarize(self) -> Dict[str, int]:
        """Return a summary of logged events."""
        logger.info(f"Summary: {self.data}")
        return self.data

if __name__ == '__main__':
    collector = AnalyticsCollector()
    collector.log_event("page_view")
    collector.log_event("page_view")
    collector.log_event("button_click")
    print("Analytics Summary:", collector.summarize())
