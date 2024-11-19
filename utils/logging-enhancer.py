import logging
from logging.handlers import RotatingFileHandler
import datetime

# Setup logging
class LoggingEnhancer:
    """Class to enhance logging functionality."""
    def __init__(self, log_file: str = 'enhanced.log', max_bytes: int = 5 * 1024 * 1024, backup_count: int = 3):
        self.logger = logging.getLogger('EnhancedLogger')
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # Rotating file handler
        file_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        self.logger.info("Logging Enhancer initialized.")

    def log_with_timestamp(self, level: str, message: str):
        """Log a message with a precise timestamp."""
        timestamp = datetime.datetime.now().isoformat()
        formatted_message = f"[{timestamp}] {message}"
        if level.lower() == 'info':
            self.logger.info(formatted_message)
        elif level.lower() == 'warning':
            self.logger.warning(formatted_message)
        elif level.lower() == 'error':
            self.logger.error(formatted_message)

if __name__ == '__main__':
    enhancer = LoggingEnhancer()
    enhancer.log_with_timestamp('info', "This is an enhanced info log.")
    enhancer.log_with_timestamp('warning', "This is an enhanced warning log.")
    enhancer.log_with_timestamp('error', "This is an enhanced error log.")
