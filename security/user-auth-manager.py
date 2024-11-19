import hashlib
import logging
from typing import Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserAuthManager:
    """Class for managing user authentication securely."""
    def __init__(self):
        self.users: Dict[str, str] = {}
        logger.info("User Authentication Manager initialized.")

    def hash_password(self, password: str) -> str:
        """Hash a password using SHA-256."""
        hashed = hashlib.sha256(password.encode()).hexdigest()
        logger.info("Password hashed.")
        return hashed

    def add_user(self, username: str, password: str):
        """Add a new user with a hashed password."""
        if username in self.users:
            logger.warning(f"User {username} already exists.")
            return
        self.users[username] = self.hash_password(password)
        logger.info(f"User {username} added.")

    def authenticate_user(self, username: str, password: str) -> bool:
        """Authenticate a user by verifying their password."""
        hashed_password = self.users.get(username)
        if not hashed_password:
            logger.warning(f"User {username} not found.")
            return False
        is_authenticated = hashed_password == self.hash_password(password)
        logger.info(f"User {username} authentication {'succeeded' if is_authenticated else 'failed'}.")
        return is_authenticated

if __name__ == '__main__':
    auth_manager = UserAuthManager()
    auth_manager.add_user("admin", "securepassword")
    is_authenticated = auth_manager.authenticate_user("admin", "securepassword")
    print(f"Authentication successful: {is_authenticated}")
