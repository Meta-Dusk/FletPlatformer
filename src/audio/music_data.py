from dataclasses import dataclass
from pathlib import Path
from typing import Literal


_MUSIC_DIR = Path("assets") / "audio" / "music"

def music_path(name: str, extension: str | Literal[".mp3", ".ogg"] = ".mp3"):
    return _MUSIC_DIR / f"{name}{extension}"

# * Sub Sound Libraries
@dataclass
class Ambience:
    forest = music_path("forest_ambience")

@dataclass
class SketchbookAlbum:
    abstraction_2023_11_29 = music_path("Sketchbook 2023-11-29", ".ogg")
    abstraction_2024_01_24_02 = music_path("Sketchbook 2024-01-24_02", ".ogg")
    abstraction_2024_03_20_02 = music_path("Sketchbook 2024-03-20_02", ".ogg")

@dataclass
class Loops:
    sketchbook = SketchbookAlbum()

# * Main Sound Library
class MusicLibrary:
    ambience = Ambience()
    loops = Loops()