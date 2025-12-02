from pathlib import Path
from importlib.metadata import version, PackageNotFoundError


def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    """Ensures value stays between min_value and max_value."""
    return max(min_value, min(value, max_value))

def pathify(path_str: str):
    """Just wraps a str path in a `Path`."""
    return Path(path_str)

def get_app_version():
    try:
        # The string here must match the 'name' in pyproject.toml
        return version("FletPlatformer")
    except PackageNotFoundError:
        # Fallback if the app isn't installed as a package (e.g., during early dev)
        return "Dev-Mode"