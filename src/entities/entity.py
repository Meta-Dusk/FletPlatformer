import random
import flet as ft
from pathlib import Path
from typing import Self, Callable, Literal

from images import Sprite

from audio.audio_manager import AudioManager
from audio.sfx_data import SFXLibrary

from utilities.values import pathify
from utilities.components import try_update

from components.popup_text import HealthText
from components.resource_bars import StaminaBar, HealthBar
from components.hud_elements import NameTag

from entities.features.hitboxes import DamageHitbox
from entities.features.entity_data import Factions, EntityStats, EntityStates, ARMOR_SCALING_CONSTANT, DebugLogs, AnimConfig, SFXRegistry
from entities.projectile import ProjectileStats

from utilities.physics import Velocity

# from managers.game_mixins import ProjectileManagerMimic

class Entity(DamageHitbox):
    """Entity base class. Handles the sprite and some states."""
    def __init__(
        self,
        sprite: Sprite,
        name: str = "Entity",
        page: ft.Page = None,
        audio_manager: AudioManager = None,
        faction: Factions = None,
        entity_list: list[Self] = None,
        projectile_manager = None,
        *,
        show_hud: bool = True,
        debug: bool = False,
        stats: EntityStats = None,
        simple_revive: bool = True,
        restrict_movement: bool = False,
        show_stamina_bar: bool = False,
        show_dash_cooldown: bool = False,
        verbose_stamina: bool = False,
        enable_flight: bool = False,
    ) -> None:
        """The main setup for all entities."""
        # Setup the DamageHitbox class
        super().__init__()
        
        # Internal setup
        self.sprite = sprite
        self.name = name
        self.page = page
        
        self.audio_manager = audio_manager
        self.projectile_manager = projectile_manager
        self.debug = debug
        
        self.faction: Factions = faction
        self._entity_list = entity_list if entity_list is not None else []
        self._show_hud: bool
        
        self.simple_revive = simple_revive
        
        self.show_stamina_bar = show_stamina_bar
        self.show_dash_cooldown = show_dash_cooldown
        self.verbose_stamina = verbose_stamina
        
        self._handler_str: str = self.name
        self.stats: EntityStats = stats if stats else EntityStats()
        self.states: EntityStates = EntityStates(
            restrict_movement=restrict_movement,
            enable_flight=enable_flight
        )
        
        if not hasattr(self, "ground_level"):
            self._ground_level: int = 0
        self.velocity: Velocity = Velocity()
        self.on_ground: bool = True
        
        # Constants
        self._LOGIC_DELAY: float = 0.016
        self._ANIMATION_DELAY: float = 0.1
        
        # Callbacks
        self.on_death: Callable[[], None] = None
        self.on_kill: Callable[[], None] = None
        
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
        self.dash_indicator: ft.Image = None
        
        # Timers
        self.healing_effect_timer: float = 0.0
        self.hit_cooldown: float = 0.0
        
        # Animation State
        self.anim_timer: float = 0.0
        self.current_frame: int = 0
        self.current_anim_state: str | Literal["idle", "run", "fall", "attack"] = "idle"
        
        self.sfx_registry = SFXRegistry()
        
        # Define your animations here (Default config)
        self.animations: dict[str, AnimConfig] = {
            "idle": AnimConfig(4, 0.1),
            "run": AnimConfig(6, 0.075),
            "fall": AnimConfig(1, 0.1),
            "attack": AnimConfig(3, 0.05, loop=False),
        }
        
        # Finalization
        print(f"\nMaking a {faction.value} entity, named; '{name}', with {self.stats}\n")
        self.show_hud = show_hud
    
    # * === PROPERTIES ===
    @property
    def ground_level(self) -> int:
        """The floor where entities rest upon."""
        return self._ground_level
    
    @ground_level.setter
    def ground_level(self, value: int) -> None:
        self._ground_level = value
        
    @property
    def show_hud(self) -> bool:
        """The HUD contains information about HP and ST."""
        return self._show_hud
    
    @show_hud.setter
    def show_hud(self, enabled: bool) -> None:
        if enabled:
            self._health_bar_stack = self._make_health_bar()
            self._update_health_bar()
            self.nametag = self._make_nametag()
            self._make_hud()
            if self.show_stamina_bar:
                self._stamina_bar_stack = self._make_stamina_bar(
                    attach_to_hud=True, verbose=self.verbose_stamina
                )
                if self.states.exhausted:
                    self._stamina_bar_stack.st_container.bgcolor = ft.Colors.YELLOW_900
                    self.stamina_bar.color = ft.Colors.RED_900
                self._update_stamina_bar()
            if self.show_dash_cooldown:
                self.dash_indicator = self._make_dash_cooldown()
        else:
            self._health_bar_stack = None
            self.nametag = None
            self.stack.controls.remove(self.hud)
            self.hud = None
            self._stamina_bar_stack = None
            self.dash_indicator = None
        try_update(self.stack)
    
    # * === ANIMATION TICKS ===
    def tick_animation(self, dt: float) -> bool:
        """
        Advances the animation timer. 
        Returns True if the sprite source changed.
        """
        # 1. Determine State (Simple State Machine)
        # You can override this method in Player/Enemy for complex logic
        new_state = "idle"
        
        if self.states.is_attacking:
            new_state = "attack"
        elif self.states.is_falling:
            new_state = "fall"
        elif self.states.is_moving:
            new_state = "run"
            
        # 2. State Change Logic
        if new_state != self.current_anim_state:
            self.current_anim_state = new_state
            self.current_frame = 0
            self.anim_timer = 0.0
            # Force update immediately on state switch
            self._update_sprite_src() 
            return True

        # 3. Timer Logic
        config = self.animations.get(self.current_anim_state)
        if not config: return False # Unknown state
        
        self.anim_timer += dt
        
        if self.anim_timer >= config.frame_duration:
            self.anim_timer = 0
            self.current_frame += 1
            
            # Loop or Clamp
            if self.current_frame >= config.frame_count:
                if config.loop:
                    self.current_frame = 0
                else:
                    self.current_frame = config.frame_count - 1
            
            # 4. Update Source
            self._update_sprite_src()
            return True
            
        return False
    
    def _tick_simple_revive(self, dt: float) -> bool:
        """
        Helper: Handles the 'Simple Revive' (Reverse Death) logic.
        """
        if not self.states.is_reviving or not self.simple_revive:
            return False
            
        # 1. Force State Name
        new_state = "revive"
        did_frame_change = False # Track updates
        
        # 2. Handle State Switch (Init to End of Death)
        if self.current_anim_state != new_state:
            self.current_anim_state = new_state
            self.anim_timer = 0.0
            
            death_config = self.animations.get("death")
            self.current_frame = (death_config.frame_count - 1) if death_config else 0
            
            self.sprite.src = self._get_spr_path("death", self.current_frame)
            did_frame_change = True # <--- Mark as changed

        # 3. Handle Timer
        else:
            death_config = self.animations.get("death")
            if not death_config: return False
            
            self.anim_timer += dt
            if self.anim_timer >= death_config.frame_duration:
                self.anim_timer = 0
                self.current_frame -= 1 # Go Backwards
                
                # Check Finish
                if self.current_frame < 0:
                    self.current_frame = 0
                    self._on_animation_finish()
                    return True # Stop here
                
                # Update Visuals
                self.sprite.src = self._get_spr_path("death", self.current_frame)
                did_frame_change = True # <--- Mark as changed
        
        # 4. Trigger SFX (NEW BLOCK)
        if did_frame_change:
            # We check for the "revive" state in the registry
            if hasattr(self, "sfx_registry"):
                events = self.sfx_registry.get("revive", self.current_frame)
                for event in events:
                    self._play_sfx(event.sfx, event.volume)
            return True
            
        return False
    
    # * === UPDATE LOOP ===
    def update(self, dt: float) -> None:
        """
        The Master Update Loop. Called every frame by the Game Loop.
        """
        # 1. Update Visuals (Animation)
        # We assume tick_animation handles its own logic/returns
        self.tick_animation(dt)
        
        # 2. Update Logic (Input / AI)
        # Only run logic if we are alive and not stunned/disabled
        if not self.states.dead and not self.states.stunned and not self.states.is_reviving:
            self.tick_logic(dt)
            
        # 3. Handle Generic Timers (Cooldowns, etc.)
        self._tick_timers(dt)
        
    def tick_logic(self, dt: float) -> None:
        """
        Override this! 
        - Players put input handling here.
        - Enemies put AI decision making here.
        """
        pass
        
    def _tick_timers(self, dt: float) -> None:
        """Handles internal cooldowns without asyncio.sleep."""
        # Example: Dash Cooldown
        if hasattr(self, "dash_cooldown_timer") and self.dash_cooldown_timer > 0:
            self.dash_cooldown_timer -= dt
        
        # Manually reset the damage flag if we ignored the stun animation
        if self.hit_cooldown > 0:
            self.hit_cooldown -= dt
            if self.hit_cooldown <= 0:
                self.states.taking_damage = False
                self._reset_tint()
        
        if not self.states.dead:
            self._tick_healing_effect(dt)
    
    def _tick_healing_effect(self, dt: float) -> None:
        """Handles the duration of the healing state/visuals."""
        if self.states.is_healing:
            self.healing_effect_timer -= dt
            
            if self.healing_effect_timer <= 0:
                self.states.is_healing = False
                self._reset_tint()
    
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
    
    def _play_sfx(self, sfx: SFXLibrary, volume: float = None) -> None:
        """Play an SFX with support for directional playback."""
        right_vol = (self.stack.left + (self.sprite.width / 2)) / self.page.width
        left_vol = 1.0 - right_vol
        self.audio_manager.play_sfx(
            sfx_path=sfx,
            left_volume=left_vol,
            right_volume=right_vol,
            base_volume=volume
        )
    
    def _play_sfx_list(self, sfx: list[SFXLibrary], volume: float = None) -> None:
        """Play a list of SFX with support for directional playback."""
        if sfx is None or len(sfx) == 0: return
        for sound in sfx:
            self._play_sfx(sound, volume)
        
    # * === COMPONENT TOGGLES ===
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
    def _update_sprite_src(self):
        """Helper to generate the path string."""
        # Uses your existing _get_spr_path helper
        self.sprite.src = self._get_spr_path(self.current_anim_state, self.current_frame)
    
    def _reset_tint(self) -> None:
        """Resets the sprite color, but respects the Exhausted state."""
        if self.states.dead: return
        
        self.sprite.color = ft.Colors.WHITE
        self.sprite.color_blend_mode = ft.BlendMode.MODULATE
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
    
    def _make_dash_cooldown(self) -> ft.Image:
        """Returns the icon for the dash cooldown."""
        _scale = 0.25
        dash_cooldown = ft.Image(
            src="images/icons/dash.png", filter_quality=ft.FilterQuality.NONE,
            scale=_scale, fit=ft.BoxFit.COVER, color_blend_mode=ft.BlendMode.MODULATE,
            left=-40, top=-22, width=256 * _scale, height=256 * _scale
        )
        
        self._health_bar_stack.controls.append(dash_cooldown)
        return dash_cooldown
    
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
            width=self.sprite.width, height=self.sprite.height,
            clip_behavior=ft.ClipBehavior.NONE
        )
    
    def _update_health_bar(self) -> None:
        """Updates the health bar if provided."""
        if self.health_bar is None: return
        self.health_bar.value = abs((self.stats.health / self.stats.max_health) - 1)
        try_update(self.health_bar)
        if self._health_bar_stack:
            self._health_bar_stack.hp_label.current_value = round(self.stats.health, 1)
    
    def _update_stamina_bar(self) -> None:
        """Updates the stamina bar if provided."""
        if self.stamina_bar is None: return
        self.stamina_bar.value = abs((self.stats.stamina / self.stats.max_stamina) - 1)
        try_update(self.stamina_bar)
        if self._stamina_bar_stack and self._stamina_bar_stack.verbose:
            self._stamina_bar_stack.st_label.current_value = round(self.stats.stamina, 1)
    
    def _get_facing_direction(self) -> Literal[-1, 1]:
        current_scale_x = self.sprite.scale.scale_x if hasattr(self.sprite.scale, "scale_x") else self.sprite.scale
        return 1 if current_scale_x > 0 else -1
    
    def _flip_sprite_x(self, dx: int) -> bool:
        """Flips the facing direction of the sprite (Data only)."""
        start_facing_sign = self._get_facing_direction()
        desired_sign = 1 if dx > 0 else -1 if dx < 0 else start_facing_sign
        
        if desired_sign != start_facing_sign:
            # Just change the property. The AnimationManager/PhysicsManager will 
            # batch update this sprite in the next frame cycle.
            self.sprite.flip_x(desired_sign, update_ctrl=False)
            
            # Flip Hitboxes (Internal logic only)
            self._flip_atk_hb()
            self._flip_self_hb()
            return True
        return False
    
    def _get_center_point(self) -> int:
        """Returns the center point aligned at the bottom stack."""
        return self.stack.left + (self.stack.width / 2)
    
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
        self.velocity.dx = 0
        knockback: int = 0
        if entity._get_center_point() > self._get_center_point():
            knockback = -entity.stats.attack_knockback * self.stats.knockback_resistance
        elif entity._get_center_point() < self._get_center_point():
            knockback = entity.stats.attack_knockback * self.stats.knockback_resistance
        self.velocity.dx += knockback
        self.velocity.dy += abs(knockback) * 1.5
    
    def attack_ranged(
        self, start_x: float = None, start_y: float = None,
        direction: Literal[-1, 1] = None,
        stats: ProjectileStats = None, src: str = "",
        sfx_upon_spawn: tuple[SFXLibrary, float] = None,
    ) -> None:
        """Shoots out a projectile."""
        direction = self._get_facing_direction()
        if start_x is None: start_x = self.stack.left + self.stack.width / 2
        if start_y is None: start_y = (self.stack.bottom + self.stack.height / 2) - 50
        
        self.projectile_manager.spawn_projectile(
            start_x=start_x, start_y=start_y,
            direction=direction,
            owner=self, stats=stats, src=src,
            sfx_upon_spawn=sfx_upon_spawn
        )
    
    def attack(self) -> bool:
        """
        Simple spam-proof implementation for `attack()`.
        Returns `False` if action is interrupted.
        """
        if self.states.is_attacking:
            # self._debug_msg(f"{self.name} is already attacking", debug_handler=self._debug_logs.attack)
            return False
        if self.states.dead:
            # self._debug_msg(f"{self.name} cannot attack while dead", debug_handler=self._debug_logs.attack)
            return False
        if self.states.taking_damage:
            # self._debug_msg(f"{self.name} cannot attack while being damaged", debug_handler=self._debug_logs.attack)
            return False
        return True
        # ? Implement the rest of the logic after calling this method
    
    def take_damage(self, damage_amount: float, is_crit: bool = False) -> bool:
        """
        Base implementation for taking damage.
        Handles: Checks, Health Subtraction, and Safety Reset.
        Returns `True` if damage was successfully applied.
        """
        if self.states.dead or self.states.taking_damage or self.states.invincible: return False
        
        if self.states.stun_immune:
            armor_amount = self.stats.armor + self.stats.stun_immune_bonus_armor
        else:
            armor_amount = self.stats.armor
        damage_reduction: float = round(ARMOR_SCALING_CONSTANT / (ARMOR_SCALING_CONSTANT + armor_amount), 1)
        _damage_amount = damage_amount * damage_reduction
        
        self.states.taking_damage = True
        
        if not self.states.stun_immune:
            self.states.stunned = True
        else:
            self.hit_cooldown = 0.2
            self._on_stun_immune_hit()
        
        self.stats.health -= _damage_amount
        
        dmg_text = HealthText(value=f"-{_damage_amount}", right=-105, top=4, color=ft.Colors.RED_ACCENT, anim_right=-80)
        self.stack.controls.append(dmg_text)
        if is_crit:
            crit_text = HealthText(value="CRIT!", right=-190, top=4, color=ft.Colors.ORANGE)
            self.stack.controls.append(crit_text)
            
        try_update(self.stack)
        return True
    
    def _on_stun_immune_hit(self):
        """
        Call this first before doing additional before,
        such as playing specific sounds or effects when resisting stun.
        """
        self._update_health_bar()
    
    def death(self) -> bool:
        """
        Simple spam-proof implementation for `death()`.
        Returns `False` if action is interrupted.
        """
        if self.states.dead:
            return False
        return True
        # ? Implement the rest of the logic after calling this method
        
    def revive(self) -> bool:
        """
        Simple spam-proof implementation for `revive()`.
        Returns `False` if action is interrupted.
        """
        if not self.states.dead or not self.states.revivable: return False
        
        self.states.is_reviving = True
        self.states.revivable = False
        
        return True
        
    def heal(self, heal_amount: float, overheal: bool = False) -> bool:
        """
        Base implementation for healing.
        Handles: Checks, Health Addition, and Safety Reset.
        Returns `True` if heal was successfully applied.
        """
        if (
            self.states.dead or
            self.stats.health >= self.stats.max_health and
            not overheal or self.states.is_healing
        ):
            return False
        
        if not overheal and (self.stats.health + heal_amount) > self.stats.max_health:
            self.stats.health = self.stats.max_health
        else:
            self.stats.health += heal_amount
            
        heal_text = HealthText(value=f"+{heal_amount}", right=-105, top=4, color=ft.Colors.GREEN_ACCENT, anim_right=-80)
        self.states.is_healing = True
        self._apply_tint(ft.Colors.GREEN)
        self._update_health_bar()
        self.healing_effect_timer = self.stats.healing_delay
        
        self.stack.controls.append(heal_text)
        try_update(self.stack)
        return True