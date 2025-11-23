import asyncio, random
import flet as ft
from ..images import Sprite
from dataclasses import dataclass


@dataclass
class EntityStates:
    """Entity states and tasks."""
    is_moving: bool = False
    sprint: bool = False
    jumped: bool = False
    attack_phase: int = 0
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
    def __init__(self, sprite: Sprite, name: str, page: ft.Page):
        self.sprite = sprite
        self.name = name
        self.page = page
        self.states = EntityStates()
        self.stats = EntityStats()
        self.stack: ft.Stack = self._make_stack()
    
    def _make_stack(self):
        return ft.Stack(
            controls=[self.sprite],
            left=(self.page.width / 2) - (self.sprite.width / 2), bottom=0,
            animate_position=ft.Animation(100, ft.AnimationCurve.EASE_IN_OUT)
        )
    
    async def _movement_loop(self):
        while True:
            dx, dy = 0, 0
            dx += self.stats.movement_speed * random.randint(-3, 3)
            self.stack.left += dx
            self.stack.bottom += dy
            
            if ( # ? Manages asset flip direction
                (dx > 0 and self.sprite.scale.scale_x < 0) or
                (dx < 0 and self.sprite.scale.scale_x > 0)
            ): self.sprite.flip_x()
            
            if self.stack.page: self.stack.update()
            await asyncio.sleep(1)
    
    def start_movement_loop(self):
        self.page.run_task(self._movement_loop)
        
    def __call__(self):
        """
        Returns the `Stack` control. Make sure to always put this
        in another stack.
        """
        return self.stack


# * Test for the Entity class
# ? Run with: uv run py -m src.entities.entity
def test(page: ft.Page):
    page.title = "Entity Class Test"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    entity_spr = Sprite("images/enemies/goblin/idle_0.png", width=180, height=180)
    entity = Entity(entity_spr, "Entity", page)
    stage = ft.Stack(controls=[entity()], expand=True)
    
    page.add(stage)
    entity.start_movement_loop()
    
if __name__ == "__main__":
    ft.run(test, assets_dir="../assets")