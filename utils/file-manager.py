import os
import logging
from typing import List

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileManager:
    """Class for managing files and directories."""
    @staticmethod
    def list_files(directory: str) -> List[str]:
        """List all files in a given directory."""
        try:
            files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
            logger.info(f"Files in {directory}: {files}")
            return files
        except FileNotFoundError:
            logger.error(f"Directory {directory} not found.")
            return []

    @staticmethod
    def create_file(file_path: str, content: str = ""):
        """Create a new file with optional content."""
        try:
            with open(file_path, 'w') as file:
                file.write(content)
            logger.info(f"File {file_path} created.")
        except Exception as e:
            logger.error(f"Error creating file {file_path}: {e}")

if __name__ == '__main__':
    directory = "."
    FileManager.list_files(directory)
    FileManager.create_file("test_file.txt", "This is a test.")
    print("Files:", FileManager.list_files(directory))
