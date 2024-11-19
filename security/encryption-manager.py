from cryptography.fernet import Fernet
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EncryptionManager:
    """Class for managing encryption and decryption."""
    def __init__(self):
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
        logger.info("Encryption Manager initialized.")

    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt a plaintext string."""
        ciphertext = self.cipher.encrypt(plaintext.encode())
        logger.info(f"Encrypted data: {ciphertext}")
        return ciphertext

    def decrypt(self, ciphertext: bytes) -> str:
        """Decrypt a ciphertext string."""
        plaintext = self.cipher.decrypt(ciphertext).decode()
        logger.info(f"Decrypted data: {plaintext}")
        return plaintext

if __name__ == '__main__':
    manager = EncryptionManager()
    encrypted = manager.encrypt("Sensitive Data")
    print("Encrypted:", encrypted)
    decrypted = manager.decrypt(encrypted)
    print("Decrypted:", decrypted)
