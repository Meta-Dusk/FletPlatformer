import asyncio, random
import flet as ft
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

from images import Sprite
from audio.audio_manager import AudioManager
from utilities.values import pathify


class Factions(Enum):
    HUMAN = "Human"
    NONHUMAN = "Non-Human"

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
    disable_movement: bool = False
    revivable: bool = False
    dealing_damage: bool = False

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
        audio_manager: AudioManager = None, faction: Factions = None,
        show_hud: bool = True, *, debug: bool = True, stats: EntityStats = None
    ):
        self.sprite = sprite
        self.name = name
        self.page = page
        self.audio_manager = audio_manager
        self.debug = debug
        self.faction: Factions = faction
        if stats is None: stats = EntityStats()
        self._handler_str: str = "Entity"
        self.states: EntityStates = EntityStates()
        self.stats: EntityStats = stats
        self.stack: ft.Stack = self._make_stack()
        self._movement_loop_task: asyncio.Task = None
        self._spr_path: Path = pathify(sprite.src)
        self.health_bar: ft.ProgressBar = None
        self.nametag: ft.Text = None
        print(f"Making a {faction.value} entity, named; \"{name}\"")
        if show_hud:
            self.health_bar = self._make_health_bar()
            self.nametag = self._make_nametag()
            self.stack.controls.append(self._make_hud())
            self._safe_update(self.stack)
    
    # * === FUNCTIONAL WRAPPERS ===
    def _debug_msg(self, msg: str, *, end: str = None, include_handler: bool = True):
        """A simple debug message for simple logging."""
        if self.debug:
            if include_handler: print(f"[{self._handler_str}] {msg}", end=end)
            else: print(msg, end=end)
    
    def _play_sfx(self, sfx: Path):
        """Play an SFX with support for directional playback."""
        right_vol = (self.stack.left + (self.sprite.width / 2)) / self.page.width
        left_vol = 1.0 - right_vol
        self.audio_manager.play_sfx(sfx, left_vol, right_vol)
    
    # * === MOVEMENT LOOP ===
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
            
            self._safe_update(self.stack)
            await asyncio.sleep(0.5)
    
    def _start_movement_loop(self):
        """Starts the movement loop and stores it in a variable."""
        self._debug_msg("Starting Movement Loop!")
        self._movement_loop_task = self.page.run_task(self._movement_loop)
    
    # * === COMPONENT METHODS ===
    def _make_hud(self):
        if self.nametag is None:
            print("Missing nametag!")
        if self.health_bar is None:
            print("Missing healthbar!")
        return ft.Container(
            ft.Column(
                controls=[self.nametag, self.health_bar],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ), top=0, left=0, right=0
        )
    
    def _make_nametag(self):
        return ft.Text(value=self.name, size=20, text_align=ft.TextAlign.CENTER)
    
    def _make_health_bar(self):
        return ft.ProgressBar(
            value=0, scale=ft.Scale(scale_x=-1, scale_y=1), color=ft.Colors.BLACK,
            bgcolor=ft.Colors.RED, border_radius=5, width=120, height=5
        )
    
    def _get_spr_path(self, state: str, index: int, *, debug: bool = False):
        """Returns a formatted str path for sprites."""
        _parent = self._spr_path.parent
        _suffix = self._spr_path.suffix
        spr_path = _parent / f"{state}_{index}{_suffix}"
        if debug: self._debug_msg(f"Generated spr_path: {spr_path}")
        return spr_path.as_posix()
    
    def _make_stack(self):
        """Returns a stack positioned at the bottom-center of the screen."""
        self._debug_msg(f"Created Entity of faction: {self.faction}")
        return ft.Stack(
            controls=[
                ft.Container(
                    self.sprite,
                    # border=ft.Border.all(2),
                    data=self.faction
                )
            ],
            left=(self.page.width / 2) - (self.sprite.width / 2), bottom=0,
            animate_position=ft.Animation(100, ft.AnimationCurve.EASE_IN_OUT)
        )
    
    def _safe_update(self, *controls: ft.Control):
        """
        Updates multiple controls safely.\n
        As of Flet version `0.70.0.dev6787`, accessing the `.page` property
        will raise a `RuntimeError` exception.
        """
        for control in controls:
            try: control.update()
            except RuntimeError: pass
    
    async def _update_health_bar(self):
        """Updates the health bar if provided."""
        if self.health_bar is None: return
        await asyncio.sleep(0.1)
        self.health_bar.value = abs((self.stats.health / self.stats.max_health) - 1)
        self._safe_update(self.health_bar)
    
    # * === OTHER HELPERS ===
    def _reset_states(self, new_states: EntityStates = None):
        """Reset entity state values back to their defaults."""
        if new_states is None: new_states = EntityStates()
        self.states = new_states
    
    def _reset_stats(self, new_stats: EntityStates = None):
        """Reset entity statistics back to their defaults."""
        if new_stats is None: new_stats = EntityStats()
        self.stats = new_stats
    
    # * === CALLABLE ACTIONS/EVENTS ===
    def __call__(self):
        """
        Returns the `Stack` control. Make sure to always put this
        in another stack.
        """
        return self.stack
    
    def attack(self):
        """
        Simple spam-proof implementation for `attack()`.
        Returns `False` if action is interrupted.
        """
        if self.states.is_attacking:
            self._debug_msg(f"{self.name} is already attacking")
            return False
        if self.states.dead:
            self._debug_msg(f"{self.name} cannot attack while dead")
            return False
        if self.states.taking_damage:
            self._debug_msg(f"{self.name} cannot attack while being damaged")
            return False
        return True
        # ? Implement the rest of the logic here
    
    def take_damage(self):
        """
        Simple spam-proof implementation for `take_damage()`.
        Returns `False` if action is interrupted.
        """
        if self.states.dead:
            self._debug_msg(f"{self.name} is already dead")
            return False
        if self.states.taking_damage:
            self._debug_msg(f"{self.name} cannot be damaged again yet")
            return False
        return True
        # ? Implement the rest of the logic here
    
    def death(self):
        """
        Simple spam-proof implementation for `death()`.
        Returns `False` if action is interrupted.
        """
        if self.states.dead:
            self._debug_msg(f"{self.name} is already dead")
            return False
        return True
        # ? Implement the rest of the logic here
        
    def revive(self):
        """
        Simple spam-proof implementation for `revive()`.
        Returns `False` if action is interrupted.
        """
        if not self.states.dead:
            self._debug_msg(f"{self.name} is not dead")
            return False
        elif not self.states.revivable:
            self._debug_msg(f"{self.name} is not yet ready to be revived")
            return False
        return True
        # ? Implement the rest of the logic here


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