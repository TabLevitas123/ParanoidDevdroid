import logging
from typing import Any, Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StabilityAIAPIClient:
    """Mock client for Stability AI API interactions."""
    def __init__(self, api_key: str, base_url: str = 'https://api.stability.ai/v1'):
        if not api_key:
            raise ValueError("API key must be provided.")
        self.api_key = api_key
        self.base_url = base_url
        logger.info("Mock Stability AI API client initialized.")

    def generate_image(self, prompt: str) -> Dict[str, Any]:
        """Simulate image generation based on a text prompt."""
        if not prompt:
            raise ValueError("Prompt must not be empty.")
        logger.info(f"Mock image generation for prompt: {prompt}")
        return {'status': 'success', 'image_url': 'http://mock-image-url.com/fake-image.jpg'}

if __name__ == '__main__':
    api_client = StabilityAIAPIClient(api_key="mock-api-key")
    prompt = "A futuristic cityscape at sunset."
    result = api_client.generate_image(prompt)
    print(result)
