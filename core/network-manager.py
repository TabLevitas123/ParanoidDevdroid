import logging
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkManager:
    """Mock class for managing network requests."""
    @staticmethod
    def send_request(url: str, method: str = 'GET', data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Simulate a network request and return a mock response."""
        logger.info(f"Simulating {method} request to {url}")
        return {"mock_response": "This is a simulated response."}

if __name__ == '__main__':
    # Example usage with a mock URL
    network_manager = NetworkManager()
    print(network_manager.send_request('https://jsonplaceholder.typicode.com/posts', 'GET'))
