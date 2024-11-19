import uuid
import time
import logging
from typing import Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SessionManager:
    """Class for managing user sessions."""
    def __init__(self):
        self.sessions: Dict[str, float] = {}
        logger.info("Session Manager initialized.")

    def create_session(self) -> str:
        """Create a new session and return its ID."""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = time.time()
        logger.info(f"Session created with ID: {session_id}")
        return session_id

    def validate_session(self, session_id: str, timeout: int = 3600) -> bool:
        """Validate a session based on its ID and timeout."""
        start_time = self.sessions.get(session_id)
        if not start_time or (time.time() - start_time > timeout):
            logger.warning(f"Session {session_id} is invalid or expired.")
            return False
        logger.info(f"Session {session_id} is valid.")
        return True

    def destroy_session(self, session_id: str):
        """Destroy a session based on its ID."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Session {session_id} destroyed.")
        else:
            logger.warning(f"Session {session_id} not found.")

if __name__ == '__main__':
    manager = SessionManager()
    session = manager.create_session()
    print("Session Valid:", manager.validate_session(session))
    time.sleep(2)
    manager.destroy_session(session)
    print("Session Valid After Destruction:", manager.validate_session(session))
