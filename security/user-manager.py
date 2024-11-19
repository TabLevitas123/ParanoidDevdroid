import logging
from typing import Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserManager:
    """Class for managing user data."""
    def __init__(self):
        self.users: Dict[str, str] = {}
        logger.info("User Manager initialized.")

    def add_user(self, username: str, password: str):
        """Add a new user."""
        if username in self.users:
            logger.warning(f"User {username} already exists.")
        else:
            self.users[username] = password
            logger.info(f"User {username} added.")

    def authenticate_user(self, username: str, password: str) -> bool:
        """Authenticate a user."""
        if self.users.get(username) == password:
            logger.info(f"User {username} authenticated successfully.")
            return True
        logger.warning(f"Authentication failed for user {username}.")
        return False

if __name__ == '__main__':
    manager = UserManager()
    manager.add_user("test_user", "password123")
    authenticated = manager.authenticate_user("test_user", "password123")
    print("Authentication Status:", authenticated)
