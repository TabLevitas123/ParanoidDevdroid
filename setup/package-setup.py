# setup_package.py

from pathlib import Path
import shutil

def setup_project_structure():
    """Setup complete project structure"""
    
    # Define project structure
    structure = {
        'ai_platform': {
            'agents': {},
            'marketplace': {},
            'services': {
                'api_integration': {}
            },
            'tokens': {},
            'users': {},
            'utils': {},
            'models': {},
            'schemas': {},
            'config': {},
        },
        'tests': {},
        'logs': {},
        'test': {
            'db': {},
            'logs': {},
            'reports': {},
            'data': {}
        }
    }

    def create_directories(base_path: Path, structure: dict):
        """Recursively create directory structure"""
        for name, substructure in structure.items():
            path = base_path / name
            path.mkdir(parents=True, exist_ok=True)
            
            # Create __init__.py for Python packages
            if name != 'logs' and name != 'test':
                init_file = path / '__init__.py'
                init_file.touch()
            
            if substructure:
                create_directories(path, substructure)

    # Create base project directory
    project_dir = Path('.')
    create_directories(project_dir, structure)
    
    print("Project structure created successfully!")

if __name__ == "__main__":
    setup_project_structure()
