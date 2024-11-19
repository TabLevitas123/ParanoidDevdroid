import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataSanitizer:
    """Class for sanitizing input data."""
    @staticmethod
    def sanitize_input(data: str) -> str:
        """Remove potentially malicious content from input data."""
        sanitized = re.sub(r"[<>\"'%;()&+]", '', data)
        logger.info(f"Input sanitized: {sanitized}")
        return sanitized

if __name__ == '__main__':
    raw_data = "<script>alert('Hacked!');</script>"
    sanitized_data = DataSanitizer.sanitize_input(raw_data)
    print("Sanitized Data:", sanitized_data)
