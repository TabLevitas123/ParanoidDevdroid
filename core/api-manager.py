import logging
from typing import Optional, Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIManager:
    """Class for managing API requests."""
    @staticmethod
    def send_request(url: str, method: str = 'GET', headers: Optional[Dict[str, str]] = None,
                     params: Optional[Dict[str, str]] = None, data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Mock API request for testing."""
        logger.info(f"Mocking {method} request to {url}")
        return {"status": "success", "message": "Mocked API response"}

if __name__ == '__main__':
    url = "https://mockapi.test/posts"
    api_manager = APIManager()
    response = api_manager.send_request(url)
    print("API Response:", response)
