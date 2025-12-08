import flet as ft
import random

from entities.enemy import Enemy, EnemyType
from entities.entity import Entity
from audio.audio_manager import AudioManager

# TODO: Transfer Goblin-specific logic here from the Enemy class

class Goblin(Enemy):
    """A preset `Enemy` class specifically for the Goblin enemy type."""
    def __init__(
        self, page: ft.Page = None, audio_manager: AudioManager = None,
        target: Enemy = None, name: str = None, entity_list: list[Entity] = None,
        *, debug: bool = False
    ) -> None:
        if name is None: name = self.generate_rnd_name()
        super().__init__(
            type=EnemyType.GOBLIN, page=page, audio_manager=audio_manager,
            target=target, name=name, entity_list=entity_list, debug=debug
        )
    
    def generate_rnd_name(self) -> None:
        """Returns a random name from the list."""
        names = ["Gobby", "Gibby", "Geeb", "Goob", "Gubby", "Gebby", "Gub", "Gerald", "Gibby", "Gib",
                "Gob", "Gobber", "Gob Lin", "Gob Gob", "Geb Geb", "Gub Gub", "Gib Gib", "Gibba", "Gibber",
                "Gob Rin", "Gobrin", "Rin"]
        return random.choice(names)