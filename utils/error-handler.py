# utils/error_handler.py

from functools import wraps
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class CustomException(Exception):
    """Base exception for application errors"""
    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"{code}: {message}")

def handle_exceptions(func):
    """Decorator for handling exceptions"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except CustomException:
            # Re-raise custom exceptions
            raise
        except Exception as e:
            # Log unexpected exceptions
            logger.exception("Unexpected error")
            # Wrap in custom exception
            raise CustomException(
                code="INTERNAL_ERROR",
                message=str(e),
                details={"type": type(e).__name__}
            )
    return wrapper
