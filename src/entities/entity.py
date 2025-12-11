import asyncio, random, inspect
import flet as ft
from pathlib import Path
from typing import Self, Callable

from images import Sprite

from audio.audio_manager import AudioManager

from utilities.values import pathify
from utilities.components import try_update, get_dur
from utilities.tasks import attempt_cancel

from components.popup_text import HealthText
from components.resource_bars import StaminaBar, HealthBar
from components.hud_elements import NameTag

from entities.features.hitboxes import DamageHitbox
from entities.features.entity_data import Factions, EntityStats, EntityStates, ARMOR_SCALING_CONSTANT, DebugLogs

class Entity(DamageHitbox):
    """Entity base class. Handles the sprite and some states."""
    def __init__(
        self, sprite: Sprite, name: str, page: ft.Page,
        audio_manager: AudioManager = None, faction: Factions = None,
        entity_list: list[Self] = None, *, show_hud: bool = True,
        debug: bool = False, stats: EntityStats = None
    ) -> None:
        """The main setup for all entities."""
        # Setup the DamageHitbox class
        super().__init__()
        
        # Internal setup
        self.sprite = sprite
        self.name = name
        self.page = page
        self.audio_manager = audio_manager
        self.debug = debug
        self.faction: Factions = faction
        self._entity_list = entity_list if entity_list is not None else []
        self.stats: EntityStats = stats if stats else EntityStats()
        self.show_hud = show_hud
        self._handler_str: str = "Entity"
        self.states: EntityStates = EntityStates()
        if not hasattr(self, "ground_level"):
            self._ground_level: int = 0
        
        # Constants
        self._LOGIC_DELAY: float = 0.1
        self._GRAVITY_VALUE: int = 25
        self._GROUNDING_VALUE: int = 10
        
        # Callbacks
        self.on_death: Callable[[], None] = None
        self.on_kill: Callable[[], None] = None
        
        # Tasks
        self._movement_loop_task: asyncio.Task = None
        self._stamina_loop_task: asyncio.Task = None
        self._health_loop_task: asyncio.Task = None
        self._jump_task: asyncio.Task = None
        self._attack_task: asyncio.Task = None
        self._take_hit_task: asyncio.Task = None
        self._animation_loop_task: asyncio.Task = None
        
        # References
        self._spr_path: Path = pathify(sprite.src)
        self._debug_logs = DebugLogs()
        
        # Toggles
        self._show_border: bool = False
        self._cleanup_ready: bool = False
        self._atk_hb_show: bool = False
        
        # Components
        self.health_bar: ft.ProgressBar = None
        self._health_bar_stack: HealthBar = None
        self.nametag: NameTag = None
        self.stamina_bar: ft.ProgressBar = None
        self._stamina_bar_stack: StaminaBar = None
        self._atk_hitboxes: list[ft.Container] = []        
        self._hitbox: ft.Container = None
        self.stack: ft.Stack = self._make_stack()
        self.hud: ft.Container = None
            
        # Finalization
        print(f"\nMaking a {faction.value} entity, named; '{name}', with {self.stats}\n")
        if self.show_hud:
            self._health_bar_stack = self._make_health_bar()
            self.nametag = self._make_nametag()
            self._make_hud()
    
    # * === PROPERTIES ===
    @property
    def ground_level(self) -> int:
        """The floor where entities rest upon."""
        return self._ground_level
    
    @ground_level.setter
    def ground_level(self, value: int) -> None:
        self._ground_level = value
    
    # * === ABSTRACT METHODS ===
    async def _take_hit_anim(play_animation: bool) -> None:
        """This will be called for when taking damage."""
        raise NotImplementedError("Implement _take_hit_anim() first!")
    
    async def _attack_anim() -> None:
        """This will be called for when attacking."""
        raise NotImplementedError("Implement _attack_anim() first!")
    
    async def _death_anim() -> None:
        """This will be called for when dying."""
        raise NotImplementedError("Implement _dying_anim() first!")
    
    async def _revive_anim() -> None:
        """This will be called for when reviving."""
        raise NotImplementedError("Implement _revive_anim() first!")
    
    async def _jump_anim() -> None:
        """This will be called for when jumping."""
        raise NotImplementedError("Implement _jump_anim() first!")
    
    async def _animation_loop(self) -> None:
        """Implement this method for entities with sprite animations."""
        raise NotImplementedError("Entity subclasses must implement the _animation_loop!")
    
    # * === FUNCTIONAL WRAPPERS ===
    def _debug_msg(
        self, msg: str, *, end: str = None, include_handler: bool = True,
        debug_handler: bool = True
    ) -> None:
        """A simple debug message for logging."""
        if not self.debug: return
        if include_handler:
            if debug_handler:
                print(f"[{self._handler_str}] {msg}", end=end)
        else:
            if debug_handler:
                print(msg, end=end)
    
    def _play_sfx(self, sfx: Path, volume: float = None) -> None:
        """Play an SFX with support for directional playback."""
        right_vol = (self.stack.left + (self.sprite.width / 2)) / self.page.width
        left_vol = 1.0 - right_vol
        self.audio_manager.play_sfx(
            sfx_path=sfx,
            left_volume=left_vol,
            right_volume=right_vol,
            base_volume=volume
        )
    
    def _play_sfx_list(self, sfx: list[Path], volume: float = None) -> None:
        """Play a list of SFX with support for directional playback."""
        if sfx is None: return
        for sound in sfx:
            self._play_sfx(sound, volume)
    
    # * === MOVEMENT LOOP ===
    def _check_movement(
        self, dx: int, dy: int,
        primary_callback: Callable[[], None] = None,
        secondary_callback: Callable[[], None] = None
    ) -> None:
        """
        Checks for movement and applies them to the `self.stack`.
        
        Args:
            primary_callback(Callable): This function is called if movement is detected.
            secondary_callback(Callable): This function is called if the facing direction has changed.
        """
        if dx != 0 or dy != 0:
            self._debug_msg(f"Moving with: ({dx}, {dy})", debug_handler=self._debug_logs.movement)
            self.states.is_moving = True
            self.stack.left += dx
            self.stack.bottom += dy
            
            if primary_callback:
                p_result = primary_callback()
                if inspect.isawaitable(p_result):
                    self.page.run_task(primary_callback)
                
            if self._flip_char(dx) and secondary_callback:
                s_result = secondary_callback()
                if inspect.isawaitable(s_result):
                    self.page.run_task(secondary_callback)
                
        else: self.states.is_moving = False
    
    async def _movement_loop(self) -> None:
        """A simple implementation of what the movement loop should be."""
        base_mv_speed = self.stack.animate_position.duration
        idle_time: float = 1.0
        
        while not self.states.dead:
            dx, dy = 0, 0
            rand_m = random.randint(-10, 10)
            
            if rand_m == 0 or random.randint(1, 10) > 8:
                idle_time = round(random.uniform(1.0, 2.0), 3)
                self._debug_msg(f"Idling for: {idle_time}s", debug_handler=self._debug_logs.movement)
                await asyncio.sleep(idle_time)
                continue
            
            dx += self.stats.movement_speed * rand_m
            self.stack.animate_position.duration = base_mv_speed * abs(rand_m)
            idle_time = get_dur(self.stack.animate_position)
            
            self._check_movement(dx, dy)
            try_update(self.stack)
            await asyncio.sleep(idle_time)    
    
    def _start_movement_loop(self) -> None:
        """Starts the movement loop and stores it in a variable."""
        self._debug_msg("Starting Movement Loop!", debug_handler=self._debug_logs.movement)
        self._movement_loop_task = self.page.run_task(self._movement_loop)
    
    # * === OTHER LOOPS ===
    def _start_animation_loop(self) -> None:
        """Starts the animation loop and stores it in a variable."""
        self._animation_loop_task = self.page.run_task(self._animation_loop)
    
    # * === COMPONENT TOGGLES ===
    def _flip_char(self, dx: int) -> bool:
        """Flips the sprite, and returns `True` if successful."""
        if self._flip_sprite_x(dx):
            self._flip_atk_hb()
            self._flip_self_hb()
            return True
        return False
    
    def toggle_show_border(self, show_border: bool = None, show_atk_hb: bool = None) -> None:
        """Toggles the bounding boxes of the entity (includes the hitbox and hurtbox)."""
        if show_border is not None: self._show_border = show_border
        else: self._show_border = not self._show_border
        if show_atk_hb is not None: self._atk_hb_show = show_atk_hb
        else: self._atk_hb_show = not self._atk_hb_show
        
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
    def _reset_tint(self) -> None:
        """Resets the tint of the sprite."""
        self.sprite.color = None
        self.sprite.color_blend_mode = ft.BlendMode.DST
        try_update(self.sprite)
    
    def _apply_tint(self, color: ft.ColorValue) -> None:
        """Applies a tint to the sprite."""
        TINT_PERCENT: float = 0.3
        self.sprite.color = ft.Colors.with_opacity(TINT_PERCENT, color)
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
    
    def _get_parent(self) -> ft.Stack:
        """Returns the stack's parent, and assumes it's also a `Stack`."""
        parent: ft.Stack = self.stack.parent
        return parent
    
    def _make_hud(self) -> None:
        """Makes the hud then attaches itself to the `stack`."""
        if self.nametag is None:
            self._debug_msg("Missing nametag!", debug_handler=self._debug_logs.setup)
        if self.health_bar is None or self._health_bar_stack is None:
            self._debug_msg("Missing healthbar!", debug_handler=self._debug_logs.setup)
        
        self.hud = ft.Container(
            ft.Column(
                controls=[self.nametag, self._health_bar_stack],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True, spacing=0
            ), top=-25, left=0, right=0, alignment=ft.Alignment.CENTER
        )
        
        self.stack.controls.append(self.hud)
        try_update(self.stack)
    
    def _make_nametag(self) -> NameTag:
        """Returns a `NameTag` custom component."""
        return NameTag(self.name)
    
    def _make_stamina_bar(self, *, verbose: bool = False, attach_to_hud: bool = False) -> StaminaBar:
        """Returns a `StaminaBar` custom component."""
        stamina_bar = StaminaBar(self.stats, verbose=verbose)
        self.stamina_bar = stamina_bar.st_bar
        if attach_to_hud and self.hud:
            hud_col: ft.Column = self.hud.content
            hud_col.controls.append(stamina_bar)
        return stamina_bar
    
    def _make_health_bar(self) -> HealthBar:
        """Returns a `HealthBar` custom component."""
        health_bar = HealthBar(self.stats, self.faction)
        self.health_bar = health_bar.hp_bar
        return health_bar
    
    def _get_spr_path(self, state: str, frame: int, *, debug: bool = False) -> str:
        """Returns a formatted str path for sprites."""
        _parent = self._spr_path.parent
        _suffix = self._spr_path.suffix
        spr_path = _parent / f"{state}_{frame}{_suffix}"
        if debug: self._debug_msg(f"Generated spr_path: {spr_path}", debug_handler=self._debug_logs.setup)
        return spr_path.as_posix()
    
    def _make_stack(self) -> ft.Stack:
        """Returns a stack positioned at the bottom-center of the screen."""
        self._debug_msg(f"Created Entity of faction: {self.faction}", debug_handler=self._debug_logs.setup)
        PAGE_CENTER_WIDTH: ft.Number = self.page.width / 2
        SPRITE_CENTER_WIDTH: ft.Number = self.sprite.width / 2
        return ft.Stack(
            controls=[ft.Container(self.sprite, data=self.faction)],
            left=PAGE_CENTER_WIDTH - SPRITE_CENTER_WIDTH, bottom=self.ground_level,
            animate_position=ft.Animation(100, ft.AnimationCurve.EASE_IN_OUT),
            width=self.sprite.width, height=self.sprite.height,
            clip_behavior=ft.ClipBehavior.NONE
        )
    
    def _update_health_bar(self) -> None:
        """Updates the health bar if provided."""
        if self.health_bar is None: return
        self.health_bar.value = abs((self.stats.health / self.stats.max_health) - 1)
        try_update(self.health_bar)
        self._health_bar_stack.hp_label.current_value = round(self.stats.health, 1)
    
    def _update_stamina_bar(self) -> None:
        """Updates the stamina bar if provided."""
        if self.stamina_bar is None: return
        self.stamina_bar.value = abs((self.stats.stamina / self.stats.max_stamina) - 1)
        try_update(self.stamina_bar)
        if self._stamina_bar_stack.verbose:
            self._stamina_bar_stack.st_label.current_value = round(self.stats.stamina, 1)
    
    def _flip_sprite_x(self, dx: int) -> bool:
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
    def _full_heal(self) -> None:
        """Sets current HP to current max HP."""
        init_stats = self._init_stats
        self.stats.health = init_stats.max_health
        
    def _reset_states(self, new_states: EntityStates = None) -> None:
        """Reset entity state values back to their defaults."""
        if new_states is None: new_states = EntityStates()
        self.states = new_states
    
    def _reset_stats(self, new_stats: EntityStates = None) -> None:
        """Reset entity statistics back to their defaults."""
        if new_stats is None: new_stats = EntityStats()
        self.stats = new_stats
    
    def _calculate_damage(self) -> tuple[float, bool]:
        """
        Checks if damage should be a critical hit.
        
        Returns:
            tuple: (`damage_amount`, `is_crit`)
        """
        is_crit: bool = False
        dmg: float = self.stats.attack_damage
        if self.stats.crit_chance >= random.randint(1, 100):
            dmg = self.stats.attack_damage * self.stats.crit_damage
            is_crit = True
        return dmg, is_crit
    
    def _cancel_temp_tasks(self):
        """Cancels all running temporary tasks."""
        tasks = [
            self._jump_task,
            self._attack_task,
            self._take_hit_task
        ]
        for task in tasks: attempt_cancel(task)
    
    def _cancel_loop_tasks(self):
        """Cancels all running looping tasks."""
        tasks = [
            self._movement_loop_task,
            self._animation_loop_task,
            self._stamina_loop_task,
            self._health_loop_task
        ]
        for task in tasks: attempt_cancel(task)
    
    # * === CALLABLE ACTIONS/EVENTS ===
    def __repr__(self) -> str:
        """
        Returns a formatted representation of the class.\n
        Example: '`Player: Hero Knight`'
        """
        # `type(self).__name__` dynamically grabs "Enemy", "Player", etc.
        return f"{type(self).__name__}: {self.name}"
    
    def __call__(self) -> ft.Stack:
        """
        Returns the `Stack` control. Make sure to
        always put this in another stack.
        """
        return self.stack
    
    def _knockback_self(self, entity: Self) -> None:
        """Applies a knockback to self away from the provided `entity`."""
        if self.states.dead: return
        knockback: int = 0
        if entity.stack.left > self.stack.left:
            knockback = -entity.stats.attack_knockback * self.stats.knockback_resistance
        elif entity.stack.left < self.stack.left:
            knockback = entity.stats.attack_knockback * self.stats.knockback_resistance
        self.stack.left += knockback
        try_update(self.stack)
    
    def attack(self) -> bool:
        """
        Simple spam-proof implementation for `attack()`.
        Returns `False` if action is interrupted.
        """
        if self.states.is_attacking:
            self._debug_msg(f"{self.name} is already attacking", debug_handler=self._debug_logs.attack)
            return False
        if self.states.dead:
            self._debug_msg(f"{self.name} cannot attack while dead", debug_handler=self._debug_logs.attack)
            return False
        if self.states.taking_damage:
            self._debug_msg(f"{self.name} cannot attack while being damaged", debug_handler=self._debug_logs.attack)
            return False
        return True
        # ? Implement the rest of the logic after calling this method
    
    def take_damage(self, damage_amount: float, is_crit: bool = False) -> bool:
        """
        Base implementation for taking damage.
        Handles: Checks, Health Subtraction, and Safety Reset.
        Returns `True` if damage was successfully applied.
        """
        if self.states.dead:
            self._debug_msg(f"{self.name} is already dead", debug_handler=self._debug_logs.damage)
            return False
        if self.states.taking_damage:
            self._debug_msg(f"{self.name} cannot be damaged again yet", debug_handler=self._debug_logs.damage)
            return False
        if self.states.invincible:
            self._debug_msg(f"{self.name} cannot be damaged during i-frames", debug_handler=self._debug_logs.damage)
            return False
        
        damage_reduction: float = round(ARMOR_SCALING_CONSTANT / (ARMOR_SCALING_CONSTANT + self.stats.armor), 1)
        _damage_amount = damage_amount * damage_reduction
        
        self.states.taking_damage = True
        self.states.stunned = True
        attempt_cancel(self._health_loop_task)
        
        self.stats.health -= _damage_amount
        damage_log = f"(-{_damage_amount} [{damage_reduction*100}% of {damage_amount}])"
        self._debug_msg(f"HP: {self.stats.health}/{self.stats.max_health} {damage_log}", debug_handler=self._debug_logs.damage)
        
        dmg_text = HealthText(value=f"-{_damage_amount}", right=-105, top=4, color=ft.Colors.RED, anim_right=-80)
        self.stack.controls.append(dmg_text)
        if is_crit:
            crit_text = HealthText(value="CRIT!", right=-190, top=4, color=ft.Colors.ORANGE)
            self.stack.controls.append(crit_text)
            
        try_update(self.stack)
        return True
    
    def death(self) -> bool:
        """
        Simple spam-proof implementation for `death()`.
        Returns `False` if action is interrupted.
        """
        if self.states.dead:
            self._debug_msg(f"{self.name} is already dead", debug_handler=self._debug_logs.death)
            return False
        return True
        # ? Implement the rest of the logic after calling this method
        
    def revive(self) -> bool:
        """
        Simple spam-proof implementation for `revive()`.
        Returns `False` if action is interrupted.
        """
        if not self.states.dead:
            self._debug_msg(f"{self.name} is not dead", debug_handler=self._debug_logs.revive)
            return False
        if not self.states.revivable:
            self._debug_msg(f"{self.name} is not yet ready to be revived", debug_handler=self._debug_logs.revive)
            return False
        return True
        # ? Implement the rest of the logic after calling this method
        
    def heal(self, heal_amount: float, overheal: bool = False) -> bool:
        """
        Base implementation for healing.
        Handles: Checks, Health Addition, and Safety Reset.
        Returns `True` if heal was successfully applied.
        """
        if self.states.dead:
            self._debug_msg(f"{self.name} is already dead", debug_handler=self._debug_logs.health)
            return False
        
        if self.stats.health >= self.stats.max_health and not overheal:
            self._debug_msg(f"{self.name} health is already at or above max", debug_handler=self._debug_logs.health)
            return False
        
        if not overheal and (self.stats.health + heal_amount) > self.stats.max_health:
            self.stats.health = self.stats.max_health
            
        self.stats.health += heal_amount
        self._debug_msg(f"HP: {self.stats.health}/{self.stats.max_health}(+{heal_amount})", debug_handler=self._debug_logs.health)
        
        heal_text = HealthText(
            left=(self.stack.width / 2) + 35, top=18,
            value=f"+{heal_amount}", color=ft.Colors.GREEN
        )
        
        self.stack.controls.append(heal_text)
        try_update(self.stack)
        return True