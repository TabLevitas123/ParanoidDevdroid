import logging
from logging.handlers import RotatingFileHandler

class LoggerManager:
    """Class for configuring and managing application loggers."""
    @staticmethod
    def get_logger(name: str, log_file: str = "app.log", level: int = logging.INFO):
        """Create and return a configured logger."""
        logger = logging.getLogger(name)
        logger.setLevel(level)

        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)

        # File handler with rotation
        file_handler = RotatingFileHandler(log_file, maxBytes=1048576, backupCount=3)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)

        # Adding handlers
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        logger.info("Logger initialized.")
        return logger

if __name__ == '__main__':
    app_logger = LoggerManager.get_logger("AppLogger", "application.log")
    app_logger.info("This is an info log.")
    app_logger.error("This is an error log.")
