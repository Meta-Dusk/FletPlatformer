from pathlib import Path


def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    """Ensures value stays between min_value and max_value."""
    return max(min_value, min(value, max_value))

def pathify(path_str: str):
    """Just wraps a str path in a `Path`."""
    return Path(path_str)