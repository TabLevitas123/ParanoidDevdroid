import logging
import traceback

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ErrorHandler:
    """Class for centralized error handling."""
    @staticmethod
    def handle_error(error: Exception):
        """Handle an error by logging and capturing its details."""
        error_details = traceback.format_exc()
        logger.error(f"An error occurred: {str(error)}")
        logger.error(f"Traceback: {error_details}")

if __name__ == '__main__':
    try:
        raise ValueError("This is a test error.")
    except Exception as e:
        ErrorHandler.handle_error(e)
