import os, sys


def get_asset_path(relative_path: str):
    """
    Returns the absolute path to an asset, working in both Dev and PyInstaller/Flet build.
    Handles the script being nested inside 'src/utilities'.
    """
    # 1. Determine the base directory where this script file is located
    # (e.g., .../src/utilities)
    current_file_path = os.path.abspath(__file__)
    utilities_dir = os.path.dirname(current_file_path)

    # 2. Go UP one level to find the 'src' (or app root) folder
    # (e.g., .../src)
    root_dir = os.path.dirname(utilities_dir)

    # 3. If frozen (built app), we might need to adjust based on how Flet extracts files
    if getattr(sys, 'frozen', False):
        # In Flet builds, usually the 'src' content is extracted to the app root.
        # If this file is still in 'utilities', going up one level is still correct.
        # However, if sys.executable is safer:
        # root_dir = os.path.dirname(sys.executable)
        pass 

    # 4. Join the root with the asset path (e.g. "assets/audio/...")
    return os.path.join(root_dir, relative_path)