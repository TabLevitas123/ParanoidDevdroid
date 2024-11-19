# organize_files.py

import os
from pathlib import Path
import shutil

def organize_files():
    """Organize project files into correct structure"""
    
    # First run package setup
    from setup_package import setup_project_structure
    setup_project_structure()
    
    # Move existing files to correct locations
    file_mappings = {
        'models/core_models.py': 'ai_platform/models/',
        'schemas/core_schemas.py': 'ai_platform/schemas/',
        'utils/logger.py': 'ai_platform/utils/',
        'utils/error_handler.py': 'ai_platform/utils/',
        'config/database.py': 'ai_platform/config/',
        'tests/master_test_runner.py': 'tests/',
        'tests/advanced_test_cases.py': 'tests/',
        'tests/api_endpoint_tests.py': 'tests/',
        'tests/transaction_tests.py': 'tests/',
        'tests/test_config.py': 'tests/',
        'tests/test_db.py': 'tests/'
    }
    
    for source, dest_dir in file_mappings.items():
        source_path = Path(source)
        if source_path.exists():
            dest_path = Path(dest_dir)
            dest_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, dest_path / source_path.name)
            print(f"Moved {source} to {dest_dir}")

    # Create required __init__.py files
    init_paths = [
        'ai_platform',
        'ai_platform/models',
        'ai_platform/schemas',
        'ai_platform/utils',
        'ai_platform/config',
        'tests'
    ]
    
    for path in init_paths:
        init_file = Path(path) / '__init__.py'
        if not init_file.exists():
            init_file.touch()
            print(f"Created {init_file}")

    print("\nFile organization complete!")

if __name__ == "__main__":
    organize_files()
