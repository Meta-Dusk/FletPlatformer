import asyncio, random
import flet as ft
from pathlib import Path
from typing import Self, Callable

from images import Sprite
from audio.audio_manager import AudioManager
from utilities.values import pathify
from utilities.components import try_update
from components.popup_text import HealthText
from entities.features.hitboxes import DamageHitbox
from entities.features.entity_data import Factions, EntityStats, EntityStates, ARMOR_SCALING_CONSTANT


class Entity(DamageHitbox):
    """Entity base class. Handles the sprite and some states."""
    def __init__(
        self, sprite: Sprite, name: str, page: ft.Page,
        audio_manager: AudioManager = None, faction: Factions = None,
        entity_list: list[Self] = None, *, show_hud: bool = True,
        debug: bool = False, stats: EntityStats = None
    ):
        super().__init__()
        self.sprite = sprite
        self.name = name
        self.page = page
        self.audio_manager = audio_manager
        self.debug = debug
        self.faction: Factions = faction
        self._entity_list = entity_list if entity_list is not None else []
        if stats is None: stats = EntityStats()
        self.stats: EntityStats = stats
        self._handler_str: str = "Entity"
        self.states: EntityStates = EntityStates()
        self._movement_loop_task: asyncio.Task = None
        self._spr_path: Path = pathify(sprite.src)
        self.health_bar: ft.ProgressBar = None
        self._health_bar_stack: ft.Stack = None
        self.nametag: ft.Stack = None
        self._show_border: bool = False
        self._cleanup_ready: bool = False
        if not hasattr(self, "_atk_hb_show"):
            self._atk_hb_show: bool = False
        self._atk_hitboxes: list[ft.Container] = []
        self._hitbox: ft.Container = None
        if not hasattr(self, "ground_level"):
            self.ground_level: int = 0
        self.stack: ft.Stack = self._make_stack()
        print(f"Making a {faction.value} entity, named; \"{name}\", with {self.stats}")
        if show_hud:
            self._health_bar_stack = self._make_health_bar()
            self.nametag = self._make_nametag()
            self.stack.controls.append(self._make_hud())
            try_update(self.stack)
    
    # * === FUNCTIONAL WRAPPERS ===
    def _debug_msg(self, msg: str, *, end: str = None, include_handler: bool = True):
        """A simple debug message for simple logging."""
        if not self.debug: return
        if include_handler: print(f"[{self._handler_str}] {msg}", end=end)
        else: print(msg, end=end)
    
    def _play_sfx(self, sfx: Path, volume: float = None):
        """Play an SFX with support for directional playback."""
        right_vol = (self.stack.left + (self.sprite.width / 2)) / self.page.width
        left_vol = 1.0 - right_vol
        self.audio_manager.play_sfx(
            sfx_path=sfx,
            left_volume=left_vol,
            right_volume=right_vol,
            base_volume=volume
        )
    
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
            if self._flip_char(dx):
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
            try_update(self.stack)
            await asyncio.sleep(idle_time)
    
    def _start_movement_loop(self):
        """Starts the movement loop and stores it in a variable."""
        self._debug_msg("Starting Movement Loop!")
        self._movement_loop_task = self.page.run_task(self._movement_loop)
    
    # * === COMPONENT TOGGLES ===
    def _flip_char(self, dx: int):
        if self._flip_sprite_x(dx):
            self._flip_atk_hb()
            self._flip_self_hb()
            return True
        return False
    
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
                    try_update(atk_hb)
        try_update(container, self._hitbox)
    
    # * === COMPONENT METHODS ===
    def _reset_tint(self):
        self.sprite.color = None
        self.sprite.color_blend_mode = ft.BlendMode.DST
        try_update(self.sprite)
    
    def _apply_tint(self, color: ft.ColorValue):
        self.sprite.color = ft.Colors.with_opacity(0.3, color)
        self.sprite.color_blend_mode = ft.BlendMode.SRC_A_TOP
        try_update(self.sprite)
    
    def _get_self_global_rect(self) -> tuple[float, float, float, float]:
        """
        Returns the **GLOBAL** (Screen) definition of the entity's body/hurtbox.
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
            self._debug_msg("Missing nametag!")
        if self.health_bar is None or self._health_bar_stack is None:
            self._debug_msg("Missing healthbar!")
        return ft.Container(
            ft.Column(
                controls=[self.nametag, self._health_bar_stack],
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
        
        stack = ft.Stack(
            controls=[outline_text, solid_text],
            clip_behavior=ft.ClipBehavior.NONE,
            alignment=ft.Alignment.CENTER
        )
        
        return stack
    
    def _make_health_bar(self):
        healthbar = ft.ProgressBar(
            value=0.0, scale=ft.Scale(scale_x=-1, scale_y=1),
            color=ft.Colors.GREY_800, bgcolor=ft.Colors.TRANSPARENT, height=18
        )
        self.health_bar = healthbar
        
        healthbar_container = ft.Container(
            width=120, border=ft.Border.all(2, ft.Colors.BLACK), border_radius=5, content=healthbar,
            bgcolor=ft.Colors.RED if self.faction == Factions.NONHUMAN else ft.Colors.GREEN
        )
        healthbar_label = ft.Text(
            color=ft.Colors.BLACK, size=18,
            spans=[
                ft.TextSpan(self.stats.health),
                ft.TextSpan("/"),
                ft.TextSpan(self.stats.max_health)
            ], left=5, top=-3
        )
        
        stack = ft.Stack(
            controls=[healthbar_container, healthbar_label],
            clip_behavior=ft.ClipBehavior.NONE,
            alignment=ft.Alignment.CENTER
        )
        
        return stack
    
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
    
    def _update_health_bar(self):
        """Updates the health bar if provided."""
        if self.health_bar is None: return
        self.health_bar.value = abs((self.stats.health / self.stats.max_health) - 1)
        label: ft.Text = self._health_bar_stack.controls[1]
        label.spans[0].text = self.stats.health
        try_update(self.health_bar, label)
    
    def _flip_sprite_x(self, dx: int):
        """Flips the facing direction of the sprite."""
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
    
    def _get_center_point(self, entity: Self) -> int:
        """Returns the center point aligned at the bottom of the entity."""
        return entity.stack.left + (entity.stack.width / 2)
    
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
    def __repr__(self):
        # type(self).__name__ dynamically grabs "Enemy", "Player", etc.
        return f"{type(self).__name__}: {self.name}"
    
    def __call__(self):
        """
        Returns the `Stack` control. Make sure to
        always put this in another stack.
        """
        return self.stack
    
    def _knockback_self(self, entity: Self):
        """Applies a knockback to self away from the provided `entity`."""
        if self.states.dead: return
        knockback: int = 0
        if entity.stack.left > self.stack.left:
            knockback = -entity.stats.attack_knockback * self.stats.knockback_resistance
        elif entity.stack.left < self.stack.left:
            knockback = entity.stats.attack_knockback * self.stats.knockback_resistance
        self.stack.left += knockback
        try_update(self.stack)
    
    def attack(self):
        """
        Simple spam-proof implementation for `attack()`.
        Returns `False` if action is interrupted.
        """
        if self.states.is_attacking:
            self._debug_msg(f"{self.name} is already attacking")
            return False
        elif self.states.dead:
            self._debug_msg(f"{self.name} cannot attack while dead")
            return False
        elif self.states.taking_damage:
            self._debug_msg(f"{self.name} cannot attack while being damaged")
            return False
        return True
        # ? Implement the rest of the logic here
    
    def take_damage(self, damage_amount: float) -> bool:
        """
        Base implementation for taking damage.
        Handles: Checks, Health Subtraction, and Safety Reset.
        Returns `True` if damage was successfully applied.
        """
        if self.states.dead:
            self._debug_msg(f"{self.name} is already dead")
            return False
        elif self.states.taking_damage:
            self._debug_msg(f"{self.name} cannot be damaged again yet")
            return False
        elif self.states.invincible:
            self._debug_msg(f"{self.name} cannot be damaged during i-frames")
            return False
        
        damage_reduction: float = ARMOR_SCALING_CONSTANT / (ARMOR_SCALING_CONSTANT + self.stats.armor)
        _damage_amount = round(damage_amount * damage_reduction, 1)
        self.states.taking_damage = True
        self.states.stunned = True
        self.stats.health -= _damage_amount
        self._debug_msg(f"HP: {self.stats.health}/{self.stats.max_health} (-{_damage_amount}[{damage_reduction*100:.2}% of {damage_amount}])")
        self.stack.controls.append(
            HealthText(
                left=(self.stack.width / 2) + 35, top=18,
                value=f"-{_damage_amount}", color=ft.Colors.RED
            )
        )
        try_update(self.stack)
        return True
    
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
        
    def heal(self, heal_amount: float, overheal: bool = False) -> bool:
        """
        Base implementation for healing.
        Handles: Checks, Health Addition, and Safety Reset.
        Returns `True` if heal was successfully applied.
        """
        if self.states.dead:
            self._debug_msg(f"{self.name} is already dead")
            return False
        
        if self.stats.health >= self.stats.max_health and not overheal:
            self._debug_msg(f"{self.name} health is already at or above max")
            return False
        
        if not overheal and (self.stats.health + heal_amount) > self.stats.max_health:
            self.stats.health = self.stats.max_health
        self.stats.health += heal_amount
        self._debug_msg(f"HP: {self.stats.health}/{self.stats.max_health}(+{heal_amount})")
        self.stack.controls.append(
            HealthText(
                left=(self.stack.width / 2) + 35, top=18,
                value=f"+{heal_amount}", color=ft.Colors.GREEN
            )
        )
        try_update(self.stack)
        return True