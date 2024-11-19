import logging
import traceback
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ErrorLogger:
    """Class for advanced error logging."""
    @staticmethod
    def log_error(error: Exception):
        """Log an error with detailed traceback."""
        error_details = traceback.format_exc()
        timestamp = datetime.utcnow().isoformat()
        logger.error(f"[{timestamp}] Error: {str(error)}")
        logger.error(f"[{timestamp}] Traceback: {error_details}")

if __name__ == '__main__':
    try:
        raise ValueError("Test error for logging.")
    except Exception as e:
        ErrorLogger.log_error(e)
