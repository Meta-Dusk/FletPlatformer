from dataclasses import dataclass
from typing import Literal

KnownExtensions = Literal["mp3", "ogg"]

def music_path(name: str, extension: str | KnownExtensions = "mp3") -> str:
    return f"audio/music/{name}.{extension}"

# * Sub Sound Libraries
@dataclass
class Ambience:
    forest = music_path("forest_ambience")

@dataclass
class SketchbookAlbum:
    abstraction_2023_11_29 = music_path("Sketchbook 2023-11-29", "ogg")
    abstraction_2024_01_24_02 = music_path("Sketchbook 2024-01-24_02", "ogg")
    abstraction_2024_03_20_02 = music_path("Sketchbook 2024-03-20_02", "ogg")

@dataclass
class Loops:
    sketchbook = SketchbookAlbum()

# * Main Sound Library
class MusicLibrary:
    """Dataclasses containing the `str` paths for available music."""
    ambience = Ambience()
    loops = Loops()