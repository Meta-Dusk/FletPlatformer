from dataclasses import dataclass


# * Sub Sound Libraries
@dataclass
class Ambience:
    forest = "audio/music/forest_ambience.mp3"

@dataclass
class SketchbookAlbum:
    abstraction_2023_11_29 = "audio/music/Sketchbook 2023-11-29.mp3"
    abstraction_2024_01_24_02 = "audio/music/Sketchbook 2024-01-24_02.mp3"
    abstraction_2024_03_20_02 = "audio/music/Sketchbook 2024-03-20_02.mp3"

@dataclass
class Loops:
    sketchbook = SketchbookAlbum()


# * Main Sound Library
class MusicLibrary:
    """Dataclasses containing the `str` paths for available music."""
    ambience = Ambience()
    loops = Loops()