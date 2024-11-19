import time
import logging
from collections import defaultdict
from typing import Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RateLimiter:
    """Class for managing API rate limiting."""
    def __init__(self, max_requests: int, window_size: int):
        self.max_requests = max_requests
        self.window_size = window_size
        self.requests: Dict[str, list] = defaultdict(list)
        logger.info("Rate Limiter initialized.")

    def is_allowed(self, user_id: str) -> bool:
        """Check if a user's request is allowed based on the rate limit."""
        current_time = time.time()
        request_times = self.requests[user_id]
        request_times = [req for req in request_times if req > current_time - self.window_size]
        self.requests[user_id] = request_times
        if len(request_times) < self.max_requests:
            self.requests[user_id].append(current_time)
            logger.info(f"Request allowed for user {user_id}.")
            return True
        logger.warning(f"Rate limit exceeded for user {user_id}.")
        return False

if __name__ == '__main__':
    limiter = RateLimiter(max_requests=3, window_size=10)
    user = "user_123"
    print(limiter.is_allowed(user))
    print(limiter.is_allowed(user))
    print(limiter.is_allowed(user))
    print(limiter.is_allowed(user))
