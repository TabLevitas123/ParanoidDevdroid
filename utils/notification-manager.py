import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationManager:
    """Class for managing notifications via email."""
    def __init__(self, smtp_server: str, smtp_port: int, sender_email: str, sender_password: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        logger.info("Notification Manager initialized.")

    def send_email(self, recipient_email: str, subject: str, body: str):
        """Simulate email notification sending."""
        logger.info(f"Simulated sending email to {recipient_email} with subject '{subject}'.")
        logger.info(f"Body: {body}")

if __name__ == '__main__':
    # Simulated usage
    notification_manager = NotificationManager(
        smtp_server='mock_smtp.example.com',
        smtp_port=587,
        sender_email='mock_email@example.com',
        sender_password='mock_password'
    )
    notification_manager.send_email(
        recipient_email='recipient@example.com',
        subject='Test Notification',
        body='This is a simulated test notification.'
    )
