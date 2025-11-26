from dataclasses import dataclass
from pathlib import Path


_MUSIC_DIR = Path("assets") / "audio" / "music"

def music_path(name: str, extension: str = ".mp3"):
    return _MUSIC_DIR / f"{name}{extension}"

# * Sub Sound Libraries
@dataclass
class Ambience:
    forest = music_path("forest_ambience")

@dataclass
class Other:
    bossa_brasil = music_path("summer-samba_world-music-bossa-brasil")
    dreams = music_path("lost-sky_dreams-ncs")

# * Main Sound Library
class MusicLibrary:
    ambience = Ambience()