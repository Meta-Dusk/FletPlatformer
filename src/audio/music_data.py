from enum import Enum
from pathlib import Path

# Define the base directory once to keep things clean
_MUSIC_DIR = Path("assets") / "audio" / "music"

class MusicList(Enum):
    """A list of available Music"""
    BOSSA_BRASIL = _MUSIC_DIR / "summer-samba_world-music-bossa-brasil.mp3"
    DREAMS = _MUSIC_DIR / "lost-sky_dreams-ncs.mp3"