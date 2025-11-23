import asyncio
import flet as ft
from images import Sprite
from dataclasses import dataclass

# TODO: Make base entity class that handles simple sprite and states

@dataclass
class EntityStates:
    """Entity states and tasks."""
    is_moving: bool = False
    sprint: bool = False
    jumped: bool = False
    jump_task: asyncio.Task = None
    attack_phase: int = 0
    attack_task: asyncio.Task = None
    is_attacking: bool = False
    is_falling: bool = False

@dataclass
class EntityStats:
    """Includes health, movement speed, etc."""
    health: float = 20
    movement_speed: int = 10
    attack_damage: float = 5
    attack_speed: float = 2

class Entity:
    """Entity base class. Handles the sprite and some states."""
    def __init__(self, sprite: Sprite, name: str):
        self.sprite = sprite
        self.name = name
        self.states = EntityStates()
        self.stats = EntityStats()
        self.dx: int = 0
        self.dy: int = 0
        self.stack: ft.Stack = self._make_stack()
    
    def _make_stack(self):
        return ft.Stack(
            controls=[self.sprite], left=0, bottom=0,
            animate_position=ft.Animation(100, ft.AnimationCurve.EASE_IN_OUT)
        )
        