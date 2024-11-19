# verify_and_run.py

import os
import sys
import subprocess
from pathlib import Path

def verify_structure():
    """Verify project structure"""
    required_dirs = [
        "models",
        "schemas",
        "tests",
        "utils",
        "config",
        "test/db",
        "test/logs",
        "test/data"
    ]
    
    for dir_path in required_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"Verified directory: {dir_path}")
    
    return True

def verify_dependencies():
    """Verify and install dependencies"""
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True
        )
        print("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install dependencies: {e}")
        return False

def run_tests():
    """Run the test suite"""
    try:
        result = subprocess.run(
            [sys.executable, "run_tests.py"],
            check=True,
            capture_output=True,
            text=True
        )
        print("\nTest Output:")
        print(result.stdout)
        
        if result.stderr:
            print("\nErrors/Warnings:")
            print(result.stderr)
            
        return True
    except subprocess.CalledProcessError as e:
        print(f"Tests failed with error: {e}")
        print("\nOutput:")
        print(e.output)
        return False

def main():
    print("Starting verification and test run...")
    
    # Verify structure
    if not verify_structure():
        print("Failed to verify project structure")
        return 1
        
    # Verify dependencies
    if not verify_dependencies():
        print("Failed to verify dependencies")
        return 1
    
    # Run tests
    if not run_tests():
        print("Tests failed")
        return 1
        
    print("All operations completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
