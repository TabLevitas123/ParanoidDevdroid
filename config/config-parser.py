import json
import logging
import os
from typing import Any, Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConfigParser:
    """Class for parsing and validating configuration files."""
    def __init__(self, config_path: str):
        self.config_path = config_path
        logger.info(f"Config Parser initialized with path: {config_path}")

    def load_config(self) -> Dict[str, Any]:
        """Load and return configuration as a dictionary."""
        if not os.path.exists(self.config_path):
            logger.error(f"Configuration file {self.config_path} does not exist.")
            raise FileNotFoundError(f"File {self.config_path} not found.")
        try:
            with open(self.config_path, 'r') as file:
                config = json.load(file)
                logger.info(f"Configuration loaded successfully: {config}")
                return config
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}")
            raise

if __name__ == '__main__':
    sample_config = {
        "app_name": "TestApp",
        "version": "1.0",
        "debug": True
    }
    sample_path = "sample_config.json"
    with open(sample_path, 'w') as file:
        json.dump(sample_config, file)

    parser = ConfigParser(sample_path)
    config = parser.load_config()
    print("Loaded Config:", config)
