import flet as ft

from entities.enemy import Enemy, EnemyType
from audio.audio_manager import AudioManager

# TODO: Make a Goblin class that will inherit from the Enemy class

class Goblin(Enemy):
    def __init__(
        self, type: EnemyType, page: ft.Page, audio_manager: AudioManager,
        target: Enemy = None, name: str = None, *, debug: bool = False
    ):
        super().__init__(type, page, audio_manager, target, name, debug=debug)
    