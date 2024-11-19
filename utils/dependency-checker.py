import importlib
import logging
from typing import List

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DependencyChecker:
    """Class for checking and managing dependencies."""
    @staticmethod
    def check_dependencies(dependencies: List[str]) -> None:
        """Check if required dependencies are installed."""
        for dependency in dependencies:
            try:
                importlib.import_module(dependency)
                logger.info(f"Dependency '{dependency}' is installed.")
            except ImportError:
                logger.error(f"Dependency '{dependency}' is missing.")
                raise ImportError(f"Dependency '{dependency}' is not installed. Please install it.")

if __name__ == '__main__':
    required_dependencies = ["os", "sys", "logging"]
    try:
        DependencyChecker.check_dependencies(required_dependencies)
        print("All dependencies are installed.")
    except ImportError as e:
        print(e)
