import jwt
import logging
import datetime
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TokenManager:
    """Class for managing tokens."""
    SECRET_KEY = "your-secret-key"

    @staticmethod
    def generate_token(data: dict, expires_in: int = 3600) -> str:
        """Generate a JWT token."""
        expiration = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)
        payload = {**data, 'exp': expiration}
        token = jwt.encode(payload, TokenManager.SECRET_KEY, algorithm='HS256')
        logger.info(f"Token generated: {token}")
        return token

    @staticmethod
    def validate_token(token: str) -> Optional[dict]:
        """Validate a JWT token."""
        try:
            payload = jwt.decode(token, TokenManager.SECRET_KEY, algorithms=['HS256'])
            logger.info(f"Token validated: {payload}")
            return payload
        except jwt.ExpiredSignatureError:
            logger.error("Token has expired.")
            return None
        except jwt.InvalidTokenError:
            logger.error("Invalid token.")
            return None

if __name__ == '__main__':
    token = TokenManager.generate_token({'user_id': 123})
    print("Generated Token:", token)
    validated_data = TokenManager.validate_token(token)
    print("Validated Data:", validated_data)
