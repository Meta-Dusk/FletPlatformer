import asyncio
import flet as ft
from entity import Entity
from ..images import Sprite


# TODO: Player class should inherit from Entity class

class Player(Entity):
    def __init__(self, page: ft.Page):
        _sprite = Sprite("images/player/idle_0.png", width=180, height=180)
        _name = "Player"
        super().__init__(sprite=_sprite, name=_name, page=page)
        self.jump_task: asyncio.Task = None
        self.attack_task: asyncio.Task = None
    
    async def _animation_loop(self):
        pass
    
    async def _jump_anim(self):
        pass
    
    async def _attack_anim(self):
        pass
    
    async def _movement_loop(self):
        pass