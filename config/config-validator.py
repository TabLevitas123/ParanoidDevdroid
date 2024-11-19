import json
import logging
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConfigValidator:
    """Class for validating configuration data."""
    @staticmethod
    def validate(config: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Validate configuration against a schema."""
        for key, value_type in schema.items():
            if key not in config or not isinstance(config[key], value_type):
                logger.error(f"Validation failed for key: {key}, Expected: {value_type}, Got: {type(config.get(key))}")
                return False
        logger.info("Configuration is valid.")
        return True

if __name__ == '__main__':
    config = {
        "app_name": "TestApp",
        "version": "1.0",
        "debug": True
    }
    schema = {
        "app_name": str,
        "version": str,
        "debug": bool
    }
    validator = ConfigValidator()
    is_valid = validator.validate(config, schema)
    print("Validation Status:", is_valid)
