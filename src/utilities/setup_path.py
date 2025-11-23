import sys
from pathlib import Path

# ? Run `configure()` if you want to make individual flet-based scripts to run

def configure():
    """Detects the project root and adds it to sys.path."""
    # 1. Get the absolute path of THIS file
    # Location: Project/src/utilities/setup_path.py
    current_file = Path(__file__).resolve()
    
    # 2. detailed walk up:
    # .parent        -> src/utilities
    # .parent.parent -> src
    # .parent.parent.parent -> Project (ROOT)
    project_root = current_file.parent.parent.parent

    # 3. Add to sys.path if not already there
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
        # print(f"[Setup] Project root added: {project_root}")
