# setup_directory.py

import os
from pathlib import Path

def create_directory_structure():
    """Create project directory structure"""
    # Root directories
    directories = [
        "agents",
        "marketplace",
        "services",
        "services/api_integration",
        "tokens",
        "users",
        "utils",
        "tests",
        "config",
        "test"
    ]
    
    # Create directories
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        # Create __init__.py in each directory
        init_file = Path(directory) / "__init__.py"
        init_file.touch()

    print("Directory structure created!")

if __name__ == "__main__":
    create_directory_structure()
