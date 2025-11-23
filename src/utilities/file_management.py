import sys
from pathlib import Path

def get_asset_path(relative_path: str) -> str:
    """
    Returns the absolute path to an asset, working in both Dev and PyInstaller/Flet build.
    Handles the script being nested inside 'src/utilities'.
    """
    
    # 1. Get the directory where this script lives (.../src/utilities)
    # We use .resolve() to get the absolute path, resolving symlinks
    current_file = Path(__file__).resolve()
    
    # 2. Determine the Root
    if getattr(sys, 'frozen', False):
        # CASE: PyInstaller / Flet Build
        # When frozen, files are often extracted to a temp folder (sys._MEIPASS)
        # If you are using 'flet pack', your assets usually end up at the root of this temp folder.
        base_path = Path(sys._MEIPASS)
    else:
        # CASE: Development
        # Go up two levels: src/utilities -> src
        base_path = current_file.parent.parent

    # 3. Join the paths using the / operator
    full_path = base_path / relative_path

    # 4. Return as a string (Flet expects strings, not Path objects)
    return str(full_path)