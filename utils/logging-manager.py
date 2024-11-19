import logging
import os
from logging.handlers import RotatingFileHandler

class LoggingManager:
    """Class for centralized logging management."""
    def __init__(self, log_file: str = 'app.log', max_bytes: int = 5 * 1024 * 1024, backup_count: int = 3):
        self.log_file = log_file
        self.max_bytes = max_bytes
        self.backup_count = backup_count

    def setup_logger(self, name: str) -> logging.Logger:
        """Set up a logger with rotation and format."""
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # File handler with rotation
        file_handler = RotatingFileHandler(self.log_file, maxBytes=self.max_bytes, backupCount=self.backup_count)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        return logger

if __name__ == '__main__':
    logging_manager = LoggingManager()
    app_logger = logging_manager.setup_logger('AppLogger')
    app_logger.info("This is an info message.")
    app_logger.warning("This is a warning message.")
    app_logger.error("This is an error message.")
