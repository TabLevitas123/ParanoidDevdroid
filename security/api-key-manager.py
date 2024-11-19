import os
import json
import logging
from cryptography.fernet import Fernet

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIKeyManager:
    """Class for securely managing API keys."""
    def __init__(self, key_file: str = 'api_keys.json', encryption_key: str = None):
        self.key_file = key_file
        self.encryption_key = encryption_key or Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)
        logger.info("API Key Manager initialized.")

    def save_api_key(self, service: str, api_key: str):
        """Save an encrypted API key to the key file."""
        encrypted_key = self.cipher.encrypt(api_key.encode()).decode()
        keys = self._load_keys()
        keys[service] = encrypted_key
        self._save_keys(keys)
        logger.info(f"API key for {service} saved.")

    def load_api_key(self, service: str) -> str:
        """Load and decrypt an API key."""
        keys = self._load_keys()
        encrypted_key = keys.get(service)
        if not encrypted_key:
            raise ValueError(f"No API key found for {service}.")
        api_key = self.cipher.decrypt(encrypted_key.encode()).decode()
        logger.info(f"API key for {service} loaded.")
        return api_key

    def _load_keys(self) -> dict:
        """Load keys from the key file."""
        if not os.path.exists(self.key_file):
            return {}
        with open(self.key_file, 'r') as file:
            return json.load(file)

    def _save_keys(self, keys: dict):
        """Save keys to the key file."""
        with open(self.key_file, 'w') as file:
            json.dump(keys, file)

if __name__ == '__main__':
    manager = APIKeyManager()
    manager.save_api_key('openai', 'mock-openai-api-key')
    print("Saved API Key.")
    api_key = manager.load_api_key('openai')
    print("Loaded API Key:", api_key)
