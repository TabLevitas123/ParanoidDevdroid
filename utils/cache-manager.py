import time
import logging
from typing import Any, Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CacheManager:
    """Class for managing a key-value cache with expiration."""
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        logger.info("Cache Manager initialized.")

    def set(self, key: str, value: Any, ttl: int = 60):
        """Set a value in the cache with an optional time-to-live."""
        expiration = time.time() + ttl
        self.cache[key] = {"value": value, "expires_at": expiration}
        logger.info(f"Key {key} set with TTL {ttl} seconds.")

    def get(self, key: str) -> Any:
        """Retrieve a value from the cache if it hasn't expired."""
        if key in self.cache:
            if time.time() < self.cache[key]["expires_at"]:
                logger.info(f"Cache hit for key {key}.")
                return self.cache[key]["value"]
            else:
                logger.info(f"Cache expired for key {key}.")
                del self.cache[key]
        logger.warning(f"Cache miss for key {key}.")
        return None

if __name__ == '__main__':
    cache = CacheManager()
    cache.set("test_key", "test_value", ttl=5)
    print("Cached Value:", cache.get("test_key"))
    time.sleep(6)
    print("Expired Value:", cache.get("test_key"))
