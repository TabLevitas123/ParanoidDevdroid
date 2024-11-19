from cryptography.fernet import Fernet
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataEncryptionManager:
    """Class for managing encryption and decryption of data."""
    def __init__(self, encryption_key: str = None):
        self.encryption_key = encryption_key or Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)
        logger.info("Data Encryption Manager initialized.")

    def encrypt_data(self, data: str) -> str:
        """Encrypt data and return the ciphertext."""
        try:
            ciphertext = self.cipher.encrypt(data.encode()).decode()
            logger.info("Data encrypted successfully.")
            return ciphertext
        except Exception as e:
            logger.error(f"Failed to encrypt data: {e}")
            raise

    def decrypt_data(self, ciphertext: str) -> str:
        """Decrypt data and return the plaintext."""
        try:
            plaintext = self.cipher.decrypt(ciphertext.encode()).decode()
            logger.info("Data decrypted successfully.")
            return plaintext
        except Exception as e:
            logger.error(f"Failed to decrypt data: {e}")
            raise

if __name__ == '__main__':
    encryption_manager = DataEncryptionManager()
    plaintext = "Sensitive information."
    encrypted = encryption_manager.encrypt_data(plaintext)
    print("Encrypted:", encrypted)
    decrypted = encryption_manager.decrypt_data(encrypted)
    print("Decrypted:", decrypted)
