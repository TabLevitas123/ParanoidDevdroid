# utils/logger.py

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

class CustomLogger:
    """Simple logger implementation"""
    
    def __init__(self, name: str, log_file: Optional[str] = None):
        # Create logs directory if needed
        if log_file:
            Path("logs").mkdir(exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Add file handler if specified
        if log_file:
            file_handler = logging.FileHandler(f"logs/{log_file}")
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def info(self, message: str):
        self.logger.info(message)
    
    def error(self, message: str):
        self.logger.error(message)
    
    def warning(self, message: str):
        self.logger.warning(message)
    
    def debug(self, message: str):
        self.logger.debug(message)

if __name__ == "__main__":
    # Test logger
    logger = CustomLogger("test", "test.log")
    logger.info("Test message")
    logger.error("Test error")
    logger.warning("Test warning")
    logger.debug("Test debug")
    print("Logger test complete")
