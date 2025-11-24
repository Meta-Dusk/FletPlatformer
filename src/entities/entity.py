import asyncio, random
import flet as ft
from dataclasses import dataclass

from images import Sprite
from audio.audio_manager import AudioManager
from audio.sfx_data import SFXList
from utilities.values import pathify


@dataclass
class EntityStates:
    """Entity states or state data."""
    is_moving: bool = False
    sprint: bool = False
    jumped: bool = False
    attack_phase: int = 0
    is_attacking: bool = False
    is_falling: bool = False
    dead: bool = False
    taking_damage: bool = False

@dataclass
class EntityStats:
    """Includes health, movement speed, etc."""
    health: float = 20
    max_health: float = 20
    movement_speed: int = 10
    attack_damage: float = 5
    attack_speed: float = 2
    jump_distance: int = 100
    jump_strength: float = 1.5
    jump_air_time: float = 0.1

class Entity:
    """Entity base class. Handles the sprite and some states."""
    def __init__(
        self, sprite: Sprite, name: str, page: ft.Page,
        audio_manager: AudioManager = None,
        *, debug: bool = True
    ):
        self.sprite = sprite
        self.name = name
        self.page = page
        self.audio_manager = audio_manager
        self.debug = debug
        self.states = EntityStates()
        self.stats = EntityStats()
        self.stack: ft.Stack = self._make_stack()
        self._movement_loop_task: asyncio.Task = None
        self._handler_str: str = "Entity"
        self._spr_path = pathify(sprite.src)
    
    def _debug_msg(self, msg: str):
        """A simple debug message for simple logging."""
        if self.debug: print(f"[{self._handler_str}] {msg}")
    
    def _play_sfx(self, sfx: SFXList):
        """Play an SFX with support for directional playback."""
        right_vol = (self.stack.left + (self.sprite.width / 2)) / self.page.width
        left_vol = 1.0 - right_vol
        self.audio_manager.play_sfx(sfx, left_vol, right_vol)
    
    def _make_stack(self):
        """Returns a stack positioned at the bottom-center of the screen."""
        return ft.Stack(
            controls=[self.sprite],
            left=(self.page.width / 2) - (self.sprite.width / 2), bottom=0,
            animate_position=ft.Animation(100, ft.AnimationCurve.EASE_IN_OUT)
        )
    
    async def _movement_loop(self):
        """A simple implementation of what the movement loop should be."""
        while not self.states.dead:
            dx, dy = 0, 0
            dx += self.stats.movement_speed * random.randint(-10, 10)
            self._debug_msg(f"Moving with: ({dx}, {dy})")
            self.stack.left += dx
            self.stack.bottom += dy
            
            if ( # ? Manages asset flip direction
                (dx > 0 and self.sprite.scale.scale_x < 0) or
                (dx < 0 and self.sprite.scale.scale_x > 0)
            ): self.sprite.flip_x()
            
            try: self.stack.update()
            except RuntimeError: pass
            await asyncio.sleep(0.5)
    
    def _start_movement_loop(self):
        """Starts the movement loop and stores it in a variable."""
        self._debug_msg("Starting Movement Loop!")
        self._movement_loop_task = self.page.run_task(self._movement_loop)
        
    def __call__(self):
        """
        Returns the `Stack` control. Make sure to always put this
        in another stack.
        """
        return self.stack
    
    def _get_spr_path(self, state: str, index: int, *, debug: bool = False):
        """Returns a formatted str path for sprites."""
        _parent = self._spr_path.parent
        _suffix = self._spr_path.suffix
        spr_path = _parent / f"{state}_{index}{_suffix}"
        if debug: self._debug_msg(f"Generated spr_path: {spr_path}")
        return spr_path.as_posix()
    
    def _update_stack(self):
        try: self.stack.update()
        except RuntimeError: pass


# * Test for the Entity class; a simple implementation
# ? Run with: uv run py -m src.entities.entity
def test(page: ft.Page):
    page.title = "Entity Class Test"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    entity_spr = Sprite("images/enemies/goblin/idle_0.png", width=150, height=150)
    entity = Entity(entity_spr, "Gob", page)
    stage = ft.Stack(controls=[entity()], expand=True)
    
    page.add(stage)
    entity._start_movement_loop()
    
if __name__ == "__main__":
    ft.run(test, assets_dir="../assets")