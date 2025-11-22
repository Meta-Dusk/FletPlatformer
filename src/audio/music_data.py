import os
from enum import Enum


class MusicList(Enum):
    """A list of available Music"""
    BOSSA_BRASIL = os.path.join("assets", "audio", "music", "summer-samba_world-music-bossa-brasil.mp3")
    DREAMS = os.path.join("assets", "audio", "music", "lost-sky_dreams-ncs.mp3")
    