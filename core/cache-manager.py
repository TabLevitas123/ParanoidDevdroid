import time
import logging
from typing import Any, Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CacheManager:
    """Class for managing in-memory caching."""
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.expiry: Dict[str, float] = {}
        logger.info("Cache Manager initialized.")

    def set(self, key: str, value: Any, ttl: int = 60):
        """Set a value in the cache with a time-to-live."""
        self.cache[key] = value
        self.expiry[key] = time.time() + ttl
        logger.info(f"Key {key} set with TTL {ttl} seconds.")

    def get(self, key: str) -> Any:
        """Get a value from the cache, if it hasn't expired."""
        if key not in self.cache or time.time() > self.expiry.get(key, 0):
            logger.warning(f"Key {key} not found or expired.")
            return None
        logger.info(f"Key {key} retrieved from cache.")
        return self.cache[key]

    def invalidate(self, key: str):
        """Invalidate a specific key in the cache."""
        if key in self.cache:
            del self.cache[key]
            del self.expiry[key]
            logger.info(f"Key {key} invalidated.")

if __name__ == '__main__':
    cache = CacheManager()
    cache.set("example", "cached value", ttl=5)
    print("Cached Value:", cache.get("example"))
    time.sleep(6)
    print("After Expiry:", cache.get("example"))
