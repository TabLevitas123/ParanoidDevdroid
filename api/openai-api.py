import openai
import logging
from typing import Any, Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenAIAPIClient:
    """Client for interacting with the OpenAI API."""
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key must be provided.")
        openai.api_key = api_key
        logger.info("OpenAI API client initialized.")

    def generate_text(self, prompt: str, max_tokens: int = 150) -> str:
        """Generate text using OpenAI's GPT model."""
        if not prompt:
            raise ValueError("Prompt must not be empty.")
        try:
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=prompt,
                max_tokens=max_tokens
            )
            # Ensure the response handles mock and real structures correctly
            generated_text = response['choices'][0]['text'].strip()
            logger.info("Text generated successfully.")
            return generated_text
        except Exception as e:
            logger.error(f"Failed to generate text: {e}")
            raise

if __name__ == '__main__':
    api_client = OpenAIAPIClient(api_key="your-api-key-here")
    prompt = "Explain the theory of relativity in simple terms."
    result = api_client.generate_text(prompt)
    print(result)
