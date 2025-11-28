import asyncio, random
import flet as ft
from dataclasses import dataclass, field, replace
from pathlib import Path
from enum import Enum
from typing import Self, Callable

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
    knockback_resistance: float = 1.0
    attack_knockback: int = 20

@dataclass
class HitboxPos:
    l_left: int = 0
    l_bottom: int = 0
    r_left: int = 0
    r_bottom: int = 0

@dataclass
class Hitbox:
    faction: Factions
    attack_phases: dict[int, HitboxPos] = field(default_factory=lambda: {
        1: HitboxPos(),
        2: HitboxPos()
    })
    current_atk_phase: int = 0

@dataclass
class SimpleHitbox:
    positions: HitboxPos = field(default_factory=lambda: HitboxPos())

class Entity:
    """Entity base class. Handles the sprite and some states."""
    def __init__(
        self, sprite: Sprite, name: str, page: ft.Page,
        audio_manager: AudioManager = None, faction: Factions = None,
        entity_list: list[Self] = None,
        *, show_hud: bool = True, debug: bool = False, stats: EntityStats = None
    ):
        self.sprite = sprite
        self.name = name
        self.page = page
        self.audio_manager = audio_manager
        self.debug = debug
        self.faction: Factions = faction
        self._entity_list = entity_list if entity_list is not None else []
        if stats is None: stats = EntityStats()
        self._handler_str: str = "Entity"
        self.states: EntityStates = EntityStates()
        self.stats: EntityStats = stats
        self._movement_loop_task: asyncio.Task = None
        self._spr_path: Path = pathify(sprite.src)
        self.health_bar: ft.ProgressBar = None
        self._health_bar_c: ft.Control = None
        self.nametag: ft.Control = None
        self._show_border: bool = False
        self._cleanup_ready: bool = False
        if not hasattr(self, "_atk_hb_show"):
            self._atk_hb_show: bool = False
        self._atk_hitboxes: list[ft.Container] = []
        self._hitbox: ft.Container = None
        self.ground_level: int = 0
        self.stack: ft.Stack = self._make_stack()
        print(f"Making a {faction.value} entity, named; \"{name}\"")
        if show_hud:
            self._health_bar_c = self._make_health_bar()
            self.nametag = self._make_nametag()
            self.stack.controls.append(self._make_hud())
            self._safe_update(self.stack)
    
    # * === DAMAGE HITBOXES ===
    def _flip_atk_hb(self):
        """Updates attack hitbox positions based on facing direction."""
        if not self._atk_hitboxes: return

        # If scale.x > 0, facing RIGHT. If < 0, facing LEFT.
        is_facing_right = self.sprite.scale.scale_x > 0
        for i, hb in enumerate(self._atk_hitboxes):
            phase_id = i + 1 # Phase 1, Phase 2...
            data: Hitbox = hb.data
            
            # Get the position config for this specific phase
            pos_config: HitboxPos = data.attack_phases.get(phase_id)
            if not pos_config: continue

            if is_facing_right: hb.left = pos_config.r_left
                # hb.bottom = pos_config.r_bottom # ? If vertical changes needed
            else: hb.left = pos_config.l_left
                # hb.bottom = pos_config.l_bottom

        # Force visual update
        self._safe_update(*self._atk_hitboxes)
    
    def _flip_self_hb(self):
        """Updates self hitbox positions based on facing direction."""
        if self._hitbox is None or self._hitbox.data is None: return

        # 1. Determine Direction
        current_scale = self.sprite.scale.scale_x if hasattr(self.sprite.scale, "scale_x") else self.sprite.scale
        is_facing_right = current_scale > 0
        
        # 2. Get Data
        data: SimpleHitbox = self._hitbox.data
        pos: HitboxPos = data.positions

        # 3. Apply Offset
        if is_facing_right:
            self._hitbox.left = pos.r_left
            self._hitbox.bottom = pos.r_bottom
        else:
            self._hitbox.left = pos.l_left
            self._hitbox.bottom = pos.l_bottom
        
        # 4. Visual Update
        self._safe_update(self._hitbox)
    
    def _make_self_hitbox(
        self, width: int = None, height: int = None,
        r_left: int = 0, bottom: int = 0
    ):
        """Makes the target-able hitbox and saves defaults."""
        if width is None: width = self.sprite.width
        if height is None: height = self.sprite.height
        
        l_left = self.sprite.width - r_left - width
        
        # Create the Position Data
        pos_data = HitboxPos(
            l_left=l_left, l_bottom=bottom,
            r_left=r_left, r_bottom=bottom
        )
        
        hb_pos_data = SimpleHitbox(pos_data)
        
        # --- NEW: Save a Backup of the Defaults ---
        # We use 'replace' to create a separate copy in memory
        self._default_self_hb_pos = replace(pos_data)
        self._default_self_hb_dims = (width, height)
        # ------------------------------------------
        
        hitbox = ft.Container(
            width=width, height=height,
            left=r_left, bottom=bottom,
            data=hb_pos_data,
        )
        
        self._hitbox = hitbox
        self.stack.controls.append(self._hitbox)
        self._safe_update(self.stack)
    
    def _make_atk_hitbox(
        self, p1_r_left: int, p1_width: int, p1_height: int,
        p2_r_left: int, p2_width: int, p2_height: int,
        bottom: int = 0
    ):
        """
        Makes the attack hitboxes for the various attack phases. Only supports two attack phases.\n
        There will be two hitboxes generated (p1, p2). Provide their local offsets with `*_r_left`.\n
        These are the offsets if the entity is facing to the right.\n
        Additionally, these offsets are _relative_ to the `self.stack`, which is where the hitboxes reside.\n
        These hitboxes must also have a `width` and a `height`.
        """
        hb_bottom = bottom
        p1_l_left = self.sprite.width - p1_r_left - p1_width # Phase 1 Config
        p2_l_left = self.sprite.width - p2_r_left - p2_width # Phase 2 Config
        
        hb_pos_data = {
            1: HitboxPos(
                l_left=p1_l_left, l_bottom=hb_bottom, 
                r_left=p1_r_left, r_bottom=hb_bottom
            ),
            2: HitboxPos(
                l_left=p2_l_left, l_bottom=hb_bottom, 
                r_left=p2_r_left, r_bottom=hb_bottom
            )
        }
        hb_data_1 = Hitbox(self.faction, hb_pos_data, 1)
        hb_data_2 = Hitbox(self.faction, hb_pos_data, 2)
        
        # Create Containers (Store them in self._atk_hitboxes)
        atk_hitbox_1 = ft.Container(
            width=p1_width, height=p1_height, 
            left=p1_r_left, bottom=hb_bottom,
            data=hb_data_1
        )
        
        atk_hitbox_2 = ft.Container(
            width=p2_width, height=p2_height, 
            left=p2_r_left, bottom=hb_bottom,
            data=hb_data_2
        )
        
        self._atk_hitboxes = [atk_hitbox_1, atk_hitbox_2]
        self.stack.controls.extend(self._atk_hitboxes)
        self._safe_update(self.stack)
    
    def _toggle_atk_hb_border(self):
        """
        Toggles the border and attack frames of the attack hitboxes.
        Also shows the next attack hitbox in the attack sequence.
        """
        if not self._atk_hb_show: return
        
        hb_count = len(self._atk_hitboxes)
        hb_next: int = 1 if hb_count == self.states.attack_phase else 2
        bgcolor = ft.Colors.with_opacity(0.15, ft.Colors.RED)
        border = ft.Border.all(1, ft.Colors.with_opacity(0.5, ft.Colors.RED))
        
        for atk_hb in self._atk_hitboxes:
            if not atk_hb.data: continue
            data: Hitbox = atk_hb.data
            
            if self.states.dead:
                atk_hb.border = None
                atk_hb.bgcolor = None
                continue
            
            if self.states.is_attacking:
                if self.states.attack_phase == data.current_atk_phase:
                    atk_hb.border = border
                    if self.states.dealing_damage: atk_hb.bgcolor = bgcolor
                    else: atk_hb.bgcolor = None
            else:
                if data.current_atk_phase == hb_next: atk_hb.border = border
                else:
                    atk_hb.border = None
                    atk_hb.bgcolor = None
            self._safe_update(atk_hb)
    
    def _modify_self_hitbox(
        self, width: int = None, height: int = None, 
        r_left: int = None, bottom: int = None,
        *, reset: bool = False
    ):
        """
        Temporarily resizes/moves the hurtbox.
        Pass `reset=True` to restore original defaults.
        """
        if self._hitbox is None or self._hitbox.data is None: return
        
        data: SimpleHitbox = self._hitbox.data
        pos: HitboxPos = data.positions
        
        # --- RESET LOGIC ---
        if reset:
            # Restore Dimensions
            width, height = self._default_self_hb_dims
            
            # Restore Positions (Copy the backup back to active data)
            # We must map the fields manually or use replace logic
            def_pos = self._default_self_hb_pos
            pos.l_left = def_pos.l_left
            pos.l_bottom = def_pos.l_bottom
            pos.r_left = def_pos.r_left
            pos.r_bottom = def_pos.r_bottom
            
            # Set local vars so visual update below works
            current_width = width
            current_height = height
            # We don't need r_left logic for reset, data is already restored
            
        else:
            # --- NORMAL LOGIC ---
            current_width = width if width is not None else self._hitbox.width
            current_height = height if height is not None else self._hitbox.height
            current_r_left = r_left if r_left is not None else pos.r_left
            current_bottom = bottom if bottom is not None else pos.r_bottom

            # Update Internal Math
            pos.r_left = current_r_left
            pos.l_left = self.sprite.width - current_r_left - current_width
            pos.r_bottom = current_bottom
            pos.l_bottom = current_bottom
        
        # --- VISUAL UPDATE ---
        self._hitbox.width = current_width
        self._hitbox.height = current_height
        
        # Apply based on facing
        current_scale = self.sprite.scale.scale_x if hasattr(self.sprite.scale, "scale_x") else self.sprite.scale
        is_facing_right = current_scale > 0
        
        if is_facing_right:
            self._hitbox.left = pos.r_left
            self._hitbox.bottom = pos.r_bottom
        else:
            self._hitbox.left = pos.l_left
            self._hitbox.bottom = pos.l_bottom
            
        self._safe_update(self._hitbox)
    
    # * === FUNCTIONAL WRAPPERS ===
    def _debug_msg(self, msg: str, *, end: str = None, include_handler: bool = True):
        """A simple debug message for simple logging."""
        if self.debug:
            if include_handler: print(f"[{self._handler_str}] {msg}", end=end)
            else: print(msg, end=end)
    
    def _play_sfx(self, sfx: Path, volume: float = None):
        """Play an SFX with support for directional playback."""
        right_vol = (self.stack.left + (self.sprite.width / 2)) / self.page.width
        left_vol = 1.0 - right_vol
        self.audio_manager.play_sfx(sfx, left_vol, right_vol, volume)
    
    # * === MOVEMENT LOOP ===
    def _check_movement(
        self, dx: int, dy: int,
        primary_callback: Callable[[None], None] = None,
        secondary_callback: Callable[[None], None] = None
    ):
        """
        Checks for movement and applies them to the `self.stack`.
        
        Args:
            primary_callback(Callable): This function is called if movement is detected.
            secondary_callback(Callable): This function is called if the facing direction has changed.
        """
        if dx != 0 or dy != 0:
            self._debug_msg(f"Moving with: ({dx}, {dy})")
            self.states.is_moving = True
            self.stack.left += dx
            self.stack.bottom += dy
            if primary_callback: primary_callback()
            
            if self._flip_sprite_x(dx):
                self._flip_atk_hb()
                self._flip_self_hb()
                if secondary_callback: secondary_callback()
        else: self.states.is_moving = False
    
    async def _movement_loop(self):
        """A simple implementation of what the movement loop should be."""
        base_mv_speed = self.stack.animate_position.duration
        while not self.states.dead:
            dx, dy = 0, 0
            rand_m = random.randint(-10, 10)
            
            if rand_m == 0 or random.randint(1, 10) > 8:
                idle_time = round(random.uniform(1.0, 2.0), 3)
                self._debug_msg(f"Idling for: {idle_time}s")
                await asyncio.sleep(idle_time)
                continue
            
            dx += self.stats.movement_speed * rand_m
            self.stack.animate_position.duration = base_mv_speed * abs(rand_m)
            idle_time = round(self.stack.animate_position.duration / 1000, 3)
            
            self._check_movement(dx, dy)
            self._safe_update(self.stack)
            await asyncio.sleep(idle_time)
    
    def _start_movement_loop(self):
        """Starts the movement loop and stores it in a variable."""
        self._debug_msg("Starting Movement Loop!")
        self._movement_loop_task = self.page.run_task(self._movement_loop)
    
    # * === COMPONENT TOGGLES ===
    def toggle_show_border(self, show_border: bool = None):
        if show_border is not None: self._show_border = show_border
        else: self._show_border = not self._show_border
        
        container: ft.Container = self.stack.controls[0]
        if self._show_border:
            container.border = ft.Border.all(1, ft.Colors.with_opacity(0.5, ft.Colors.WHITE))
            if self._hitbox:
                self._hitbox.border = ft.Border.all(1, ft.Colors.with_opacity(0.5, ft.Colors.BLUE))
                self._hitbox.bgcolor = ft.Colors.with_opacity(0.15, ft.Colors.BLUE)
        else:
            container.border = None
            if self._hitbox:
                self._hitbox.border = None
                self._hitbox.bgcolor = None
            if self._atk_hitboxes:
                for atk_hb in self._atk_hitboxes:
                    atk_hb.border = None
                    atk_hb.bgcolor = None
                    self._safe_update(atk_hb)
        self._safe_update(container, self._hitbox)
    
    def _knockback_self(self, entity: Self):
        """Applies a knockback to self based from the provided `entity`."""
        if self.states.dead: return
        knockback: int = 0
        if entity.stack.left > self.stack.left:
            knockback = -entity.stats.attack_knockback * self.stats.knockback_resistance
        elif entity.stack.left < self.stack.left:
            knockback = entity.stats.attack_knockback * self.stats.knockback_resistance
        self.stack.left += knockback
        self._safe_update(self.stack)
    
    # * === COMPONENT METHODS ===
    def _get_self_global_rect(self) -> tuple[float, float, float, float]:
        """
        Returns the GLOBAL (Screen) definition of the entity's body/hurtbox.
        Format: (left, bottom, width, height)
        """
        if self._hitbox:
            # Use the dedicated hitbox
            g_left = self.stack.left + (self._hitbox.left or 0)
            g_bottom = self.stack.bottom + (self._hitbox.bottom or 0)
            return g_left, g_bottom, self._hitbox.width, self._hitbox.height
        else:
            # Fallback to Sprite bounds if no hitbox exists
            return self.stack.left, self.stack.bottom, self.sprite.width, self.sprite.height
    
    def _get_parent(self):
        """Returns the stack's parent, and assumes it's also a `Stack`."""
        parent: ft.Stack = self.stack.parent
        return parent
    
    def _make_hud(self):
        if self.nametag is None:
            print("Missing nametag!")
        if self.health_bar is None or self._health_bar_c is None:
            print("Missing healthbar!")
        return ft.Container(
            ft.Column(
                controls=[self.nametag, self._health_bar_c],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True
            ), top=-20, left=0, right=0
        )
    
    def _make_nametag(self):
        outline_text = ft.Text(
            value=self.name, size=20,
            style=ft.TextStyle(
                foreground=ft.Paint(
                    color=ft.Colors.BLACK,
                    stroke_width=4,
                    style=ft.PaintingStyle.STROKE
                )
            ),
        )
        
        solid_text = ft.Text(value=self.name, size=20, color=ft.Colors.WHITE)
        
        return ft.Stack([outline_text, solid_text])
    
    def _make_health_bar(self):
        healthbar = ft.ProgressBar(
            value=0.0, scale=ft.Scale(scale_x=-1, scale_y=1),
            color=ft.Colors.GREY_800, bgcolor=ft.Colors.TRANSPARENT, height=15
        )
        self.health_bar = healthbar
        return ft.Container(
            width=120, height=15, border=ft.Border.all(2, ft.Colors.BLACK),
            border_radius=5, content=healthbar,
            bgcolor=ft.Colors.RED if self.faction == Factions.NONHUMAN else ft.Colors.GREEN
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
            controls=[ft.Container(self.sprite, data=self.faction)],
            left=(self.page.width / 2) - (self.sprite.width / 2), bottom=self.ground_level,
            animate_position=ft.Animation(100, ft.AnimationCurve.EASE_IN_OUT),
            width=self.sprite.width, height=self.sprite.height,
            clip_behavior=ft.ClipBehavior.NONE
        )
    
    def _safe_update(self, *controls: ft.Control):
        """
        Updates multiple controls safely.\n
        As of Flet version `0.70.0.dev6787`, accessing the `.page` property
        will raise a `RuntimeError` exception.
        """
        for control in controls:
            if control is None: continue
            try: control.update()
            except RuntimeError: pass
    
    async def _update_health_bar(self):
        """Updates the health bar if provided."""
        if self.health_bar is None: return
        await asyncio.sleep(0.1)
        self.health_bar.value = abs((self.stats.health / self.stats.max_health) - 1)
        self._safe_update(self.health_bar)
    
    def _flip_sprite_x(self, dx: int):
        current_scale_x = self.sprite.scale.scale_x if hasattr(self.sprite.scale, "scale_x") else self.sprite.scale
        start_facing_sign = 1 if current_scale_x > 0 else -1
        desired_sign = start_facing_sign
        if dx > 0: desired_sign = 1
        elif dx < 0: desired_sign = -1
        has_flipped = False
        if desired_sign != start_facing_sign:
            self.sprite.flip_x(desired_sign)
            has_flipped = True
        return has_flipped
    
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
        Returns the `Stack` control. Make sure to
        always put this in another stack.
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
