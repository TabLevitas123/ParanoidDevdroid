# utils/logger.py
import logging
from datetime import datetime
from pathlib import Path

class CustomLogger:
    def __init__(self, name: str, log_file: str = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler if specified
        if log_file:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            file_handler = logging.FileHandler(log_dir / log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def debug(self, msg: str):
        self.logger.debug(msg)
        
    def info(self, msg: str):
        self.logger.info(msg)
        
    def warning(self, msg: str):
        self.logger.warning(msg)
        
    def error(self, msg: str):
        self.logger.error(msg)
        
    def critical(self, msg: str):
        self.logger.critical(msg)

# utils/error_handler.py
from typing import Dict, Any, Optional

class CustomException(Exception):
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

def handle_exceptions(func):
    """Decorator for handling exceptions"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except CustomException as e:
            # Re-raise custom exceptions
            raise
        except Exception as e:
            # Wrap unknown exceptions
            raise CustomException(
                "INTERNAL_ERROR",
                str(e),
                {"original_error": str(e)}
            )
    return wrapper

# utils/validation_utils.py
import re
from typing import Dict, Any

class Validator:
    @staticmethod
    def validate_email(email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        issues = []
        if len(password) < 8:
            issues.append("Password must be at least 8 characters")
        if not re.search(r'[A-Z]', password):
            issues.append("Password must contain uppercase letter")
        if not re.search(r'[a-z]', password):
            issues.append("Password must contain lowercase letter")
        if not re.search(r'\d', password):
            issues.append("Password must contain digit")
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    @staticmethod
    def validate_token_amount(amount: float) -> bool:
        return amount > 0
