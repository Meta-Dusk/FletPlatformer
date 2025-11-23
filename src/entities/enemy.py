from src.utilities import setup_path
setup_path.configure()

import asyncio
import flet as ft
from src.entities.entity import Entity
from src.images import Sprite
from dataclasses import dataclass
from enum import Enum

# TODO: Enemy class should inherit from entity class

@dataclass
class EnemyData:
    name: str
    width: ft.Number
    height: ft.Number

class EnemyType(Enum):
    """Available enemy types."""
    # FLYING_EYE = EnemyData("Flying Eye", 150, 150)
    GOBLIN = EnemyData("Goblin", 150, 150)
    # MUSHROOM = EnemyData("Mushroom", 150, 150)
    # SKELETON = EnemyData("Skeleton", 150, 150)

class Enemy(Entity):
    def __init__(self, type: EnemyType, page: ft.Page):
        _sprite = Sprite(
            f"images/enemies/{type.name.lower()}/idle_0.png",
            width=type.value.width, height=type.value.height
        )
        _name = type.value.name
        super().__init__(sprite=_sprite, name=_name, page=page)
        self.attack_task: asyncio.Task = None
        
    async def _animation_loop(self):
        pass
    
    async def _attack_anim(self):
        pass