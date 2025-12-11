import asyncio, inspect
import flet as ft
from pynput import keyboard
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from entities.entity import Entity
from entities.features.entity_data import EntityStates, EntityStats, Factions

from images import Sprite

from audio.audio_manager import AudioManager
from audio.sfx_data import SFXLibrary

from utilities.tasks import attempt_cancel
from utilities.collisions import check_collision
from utilities.components import try_update
from utilities.keyboard_manager import held_keys_set

@dataclass
class PlayerData:
    name: str = "Unknown Player"
    width: ft.Number = 180
    height: ft.Number = 180

class PlayerType(Enum):
    """Available player types."""
    HERO_KNIGHT = PlayerData(name="Hero Knight")
    KING = PlayerData(name="King") # ! Not yet implemented

AnimState = Literal["moving", "falling", "idle"]

@dataclass
class SFXEvent:
    sfx: SFXLibrary
    volume: float

class SFXRegistry:
    def __init__(self):
        # Internal storage: (state, frame) -> SFXEvent
        self._data: dict[tuple[AnimState, int], SFXEvent] = {}
        
    def add(self, state: AnimState, sfx: 'SFXLibrary', volume: float = 1.0, *, frame: int):
        """
        Registers an SFX event.
        Type hints will work perfectly for 'state' here.
        """
        self._data[(state, frame)] = SFXEvent(sfx, volume)
        
    def get(self, state: AnimState, frame: int) -> SFXEvent | None:
        return self._data.get((state, frame))

sfx = SFXLibrary()

class Player(Entity):
    """Handles the player's actions and states."""
    def __init__(
        self, page: ft.Page, audio_manager: AudioManager, sprite: Sprite,
        held_keys: held_keys_set, entity_list: list[Entity] = None, name: str = None,
        *, debug: bool = False, verbose_stamina: bool = False, type: PlayerType,
        stats: EntityStats
    ):
        """The main setup for all player entities."""
        # ? Entity inherited class setup
        self._player_name = type.name.lower()
        self.name = type.value.name if name is None else name
        self._init_stats = stats
        
        super().__init__(
            sprite=sprite, name=self.name, page=page,
            audio_manager=audio_manager, faction=Factions.HUMAN,
            entity_list=entity_list, debug=debug, stats=self._init_stats
        )
        
        # ? Player setup
        self.type = type
        self.held_keys = held_keys
        self._handler_str = self.name
        
        self._has_dashed: bool = False
        self._stamina_bar_stack = self._make_stamina_bar(attach_to_hud=True, verbose=verbose_stamina)
        self.dash_indicator = self._make_dash_cooldown()
        
        # Sound effects
        self.landing_sfx_list: list[SFXLibrary] = []
        self.looking_away_sfx_list: list[SFXLibrary] = []
    
    # * === LOOPING ANIMATIONS ===
    async def _animation_loop(
        self, *, running_frame_duration: float = 0.05,
        walking_frame_duration: float = 0.075,
        idle_frame_duration: float = 0.075,
        falling_frames: int = None,
        movement_frames: int = None,
        idle_frames: int = None,
        starting_frame: int = 0,
        sfx_map: SFXRegistry  = None
    ):
        """Handles the player's different animation loops."""
        frame: int = starting_frame
        if (
            falling_frames is None or
            movement_frames is None or
            idle_frames is None
        ):
            raise ValueError("Missing arguments for '_animation_loop'!")
        
        while not self.states.dead:            
            # Give way to other animations
            if self._interrupt_action():
                await asyncio.sleep(self._LOGIC_DELAY)
                continue
            
            exhausted_frame_duration: float = walking_frame_duration * self.stats.exhaustion_modifier
            
            def play_sfx(state: AnimState) -> None:
                """Play SFX specific to state and frame."""
                if sfx_map is None: return
                nonlocal frame
                sfx_event = sfx_map.get(state, frame)
                if sfx_event: self._play_sfx(sfx_event.sfx, sfx_event.volume)
            
            # Falling animation
            if self.states.is_falling:
                if frame > falling_frames: frame = 0
                await asyncio.sleep(self._LOGIC_DELAY)
                self.sprite.change_src(self._get_spr_path("fall", frame))
                play_sfx("falling")
            
            # Running animation
            if self.states.is_moving and not self.states.is_falling:
                if frame > movement_frames: frame = 0
                if self.states.is_sprinting and not self.states.exhausted:
                    wait_time = running_frame_duration
                else:
                    if self.states.exhausted:
                        wait_time = exhausted_frame_duration
                    else:
                        wait_time = walking_frame_duration
                        
                await asyncio.sleep(wait_time)
                self.sprite.change_src(self._get_spr_path("run", frame))
                
                play_sfx("moving")
                
            # Idle animation
            elif not self.states.is_moving and not self.states.is_falling:
                if frame > idle_frames: frame = 0
                await asyncio.sleep(idle_frame_duration)
                self.sprite.change_src(self._get_spr_path("idle", frame))
                play_sfx("idle")
            
            frame += 1
    
    # * === DAMAGE DETECTION ===
    async def _detect_damage(self):
        """Checks if any hostile entity is attacking and colliding with the player."""
        if self._entity_list is None or self.states.dead or self.states.taking_damage: return
        
        # Get Player's Body Rect
        p_left, p_bottom, p_w, p_h = self._get_self_global_rect()
        
        for entity in self._entity_list:
            if (
                entity.faction != Factions.HUMAN 
                and not entity.states.dead 
                and entity.states.dealing_damage
            ):
                # Phase 1 -> Index 0, Phase 2 -> Index 1
                phase_idx = entity.states.attack_phase - 1
                
                if hasattr(entity, "_atk_hitboxes") and entity._atk_hitboxes:
                    atk_hb = entity._atk_hitboxes[phase_idx]
                    
                    # ? Calculate Global Position of Enemy's Hitbox
                    # The hitbox .left is relative to the Enemy's Stack.
                    e_hb_left = entity.stack.left + (atk_hb.left or 0)
                    e_hb_bottom = entity.stack.bottom + (atk_hb.bottom or 0)
                    
                    if check_collision(
                        r1_left=p_left, r1_bottom=p_bottom, r1_w=p_w, r1_h=p_h, # Player Body
                        r2_left=e_hb_left, r2_bottom=e_hb_bottom, r2_w=atk_hb.width, r2_h=atk_hb.height # Enemy Weapon
                    ):
                        self._debug_msg(f"Hit by {entity.name}!", debug_handler=self._debug_logs.damage)
                        await self.take_damage(*self._calculate_damage())
                        self._knockback_self(entity)
                        return
    
    async def _handle_hit_logic(self, target_enemy: Entity):
        """Applies damage to a specific enemy and updates game stats if they die."""
        # Apply Damage
        did_die = target_enemy.take_damage(*self._calculate_damage())
        
        # Check Result
        if not did_die: return
        if self.on_kill:
            result = self.on_kill()
            if inspect.isawaitable(result): await result
    
    async def _detect_attack_hits(self):
        """Checks if the Player's active attack hitbox collides with any enemy."""
        if not self.states.dealing_damage or not self._entity_list: return
        
        # ... (Get Active Hitbox logic) ...
        hb_index = self.states.attack_phase - 1
        active_hb = self._atk_hitboxes[hb_index]
        
        # Player Weapon Global Coords
        w_left = self.stack.left + (active_hb.left or 0)
        w_bottom = self.stack.bottom + (active_hb.bottom or 0)
        
        for enemy in self._entity_list:
            if enemy.faction == Factions.HUMAN or enemy.states.dead: continue
            
            # Get Enemy's Body Rect
            e_left, e_bottom, e_w, e_h = enemy._get_self_global_rect()

            if check_collision(
                r1_left=w_left, r1_bottom=w_bottom, r1_w=active_hb.width, r1_h=active_hb.height, # Player Weapon
                r2_left=e_left, r2_bottom=e_bottom, r2_w=e_w, r2_h=e_h # Enemy Body
            ):
                self._debug_msg(f"Hit enemy: {enemy.name}", debug_handler=self._debug_logs.attack)
                await self._handle_hit_logic(enemy)
    
    # * === CUSTOM MOVEMENT LOOP ===
    async def _movement_loop(self):
        """Handles player movements."""
        MV_DELAY: float = 0.05
        while True:
            await self._detect_attack_hits()
            await self._detect_damage()
            if (
                self.page.window.focused and
                not self.states.is_attacking and
                not self.states.taking_damage and
                not self.states.dead and
                not self.states.disable_movement
            ):
                is_shift_held = keyboard.Key.shift in self.held_keys
                if is_shift_held and self.stats.stamina > 0 and not self.states.exhausted:
                    step = int(self.stats.movement_speed * self.stats.sprint_mult)
                else:
                    if self.states.exhausted:
                        step = int(self.stats.movement_speed * self.stats.exhaustion_modifier)
                    else:
                        step = self.stats.movement_speed
                dx, dy = 0, 0
                
                if 'a' in self.held_keys: dx -= step
                if 'd' in self.held_keys: dx += step
                if ('a' or 'd') and 'c' in self.held_keys: await self.dash(dx)
                if ( # ? Stops moving beyond the page's borders
                    self.stack.left + dx < 0 or
                    self.stack.left + self.sprite.width + dx > self.page.width
                ): dx = 0
                
                # ? Movement
                def primary_callback():
                    self.states.is_sprinting = True if is_shift_held else False
                    if self.states.is_sprinting and self.stats.stamina > 0:
                        self.stats.stamina -= self.stats.st_usage_tick
                        self._update_stamina_bar()
                    elif self.stats.stamina <= 0:
                        self.states.exhausted = True
                        self.stats.stamina = 0
                
                self._check_movement(
                    dx, dy, primary_callback=primary_callback,
                    secondary_callback=lambda: self._play_sfx_list(self.looking_away_sfx_list)
                )
                
            else:
                # ? Reset state if doing nothing or window not focused
                self.states.is_moving = False
                self.states.is_sprinting = False
            
            # ? Grounding
            if self.stack.bottom < self.ground_level:
                self.stack.bottom += self._GROUNDING_VALUE
                if self.stack.bottom > self.ground_level: self.stack.bottom = self.ground_level
                
            # ? Gravity
            elif self.stack.bottom > self.ground_level and not self.states.jumped:
                self.states.is_falling = True
                self.stack.bottom -= self._GRAVITY_VALUE
                
                # ? Landing Logic
                if self.stack.bottom <= self.ground_level:
                    self.stack.bottom = self.ground_level
                    self._play_sfx_list(self.landing_sfx_list)
                
            elif self.stack.bottom == self.ground_level: self.states.is_falling = False
            if self.states.is_moving or self.states.is_falling: try_update(self.stack)
            await asyncio.sleep(MV_DELAY)
    
    # * === DASH COOLDOWN ===
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
    
    # * === CALLABLE PLAYER ACTIONS/EVENTS ===
    async def death(self) -> None:
        """Cancels all running tasks, and plays the death animation."""
        if not super().death(): return
        self._debug_msg(f"{self.name} has died!", debug_handler=self._debug_logs.death)
        self._reset_states(EntityStates(dead=True))
        self._reset_stats(EntityStats(health=0))
        
        attempt_cancel(self._animation_loop_task)
        attempt_cancel(self._health_loop_task)
        attempt_cancel(self._stamina_loop_task)
        self._cancel_temp_tasks()
        if self.on_death:
            result = self.on_death()
            if inspect.isawaitable(result):
                await result
        
        await self._death_anim()
        self._toggle_atk_hb_border()
    
    async def dash(self, dx: int) -> None:
        """Player dash action."""
        if self._has_dashed: return
        elif dx == 0: return
        elif self.stats.stamina <= 0: return
        elif (self.stats.stamina - self.stats.dash_st_cost) <= 0: return
        
        self._debug_msg(f"Dashing to the {"left" if dx < 0 else "right"}!", debug_handler=self._debug_logs.dash)
        self._has_dashed = True
        self.states.invincible = True
        self.stats.stamina -= self.stats.dash_st_cost
        self._update_stamina_bar()
        self._apply_tint(ft.Colors.PURPLE)
        
        if dx > 0: self.stack.left += self._get_dash_dx()
        else: self.stack.left -= self._get_dash_dx()
        self._play_sfx(sfx.whoosh.motion, 0.5)
        try_update(self.stack)
        
        async def timer() -> None:
            """Handles the dash cooldown."""
            cooldown = round(self.stats.dash_cooldown - self.stats.dash_inv_time, 3)
            await asyncio.sleep(self.stats.dash_inv_time)
            self._reset_tint()
            self.states.invincible = False
            await asyncio.sleep(cooldown)
            self._has_dashed = False
            self.dash_indicator.color = None
            try_update(self.dash_indicator)
            
        self.page.run_task(timer)
        self.dash_indicator.color = ft.Colors.with_opacity(0.75, ft.Colors.GREY)
        try_update(self.dash_indicator)
    
    def jump(self) -> None:
        """Player jump action."""
        if self.stack.bottom != self.ground_level or self._interrupt_action(): return
        elif self.stats.stamina <= 0: return
        elif (self.stats.stamina - self.stats.jump_st_cost) <= 0: return
        elif self.states.exhausted: return
        
        self.stats.stamina -= self.stats.jump_st_cost
        self._update_stamina_bar()
        self.stack.bottom += self._get_jump_dy()
        try_update(self.stack)
        self.states.jumped = True
        self._jump_task = self.page.run_task(self._jump_anim)
    
    def attack(self) -> None:
        """Player attack. Combo cycles: 1 -> 2 -> 1."""
        if not super().attack(): return
        self.states.attack_phase += 1
        if self.states.attack_phase > 2 or self.states.jumped: self.states.attack_phase = 1
        self._debug_msg(f"Attacking! Phase: {self.states.attack_phase}", debug_handler=self._debug_logs.attack)
        self.states.is_attacking = True
        self._attack_task = self.page.run_task(self._attack_anim)
        
    async def take_damage(self, damage_amount: float, is_crit: bool = False) -> None:
        """Decrease player's health with logic."""
        if not super().take_damage(damage_amount, is_crit): return
        
        if self.states.is_attacking:
            attempt_cancel(self._attack_task)
            self.states.is_attacking = False
            self.states.dealing_damage = False
            self._toggle_atk_hb_border()
            self._modify_self_hitbox(reset=True)
            
        self._apply_tint(ft.Colors.RED)
        
        if self.stats.health <= 0: await self.death()
        else:
            if self._take_hit_task: attempt_cancel(self._take_hit_task)
            self._take_hit_task = self.page.run_task(self._take_hit_anim)
    
    async def heal(self, heal_amount: float, overheal: bool = False) -> None:
        """Heals the player."""
        if not super().heal(heal_amount, overheal): return
        self._update_health_bar()
        self._apply_tint(ft.Colors.GREEN)
        await asyncio.sleep(0.1)
        self._reset_tint()
    
    async def revive(self) -> None:
        """Revives the player."""
        if not super().revive(): return
        self.states.revivable = False
        self._debug_msg(f"Reviving: {self.name}", debug_handler=self._debug_logs.revive)
        await self._revive_anim()
        self._reset_states()
        self._full_heal()
        self._reset_tint()
        attempt_cancel(self._movement_loop_task)
        self._update_health_bar()
        self._start_loops()
    
    def __call__(self, start_loops: bool = True) -> ft.Stack:
        """
        Returns the `Stack` control, and starts the movement and
        animation loops.
        """
        if start_loops: self._start_loops()
        return super().__call__()
    
    # * === RESOURCE LOOPS ===
    async def _stamina_regen_loop(self) -> None:
        """Handles the natural stamina regen loop."""
        while not self.states.dead:
            if self.stats.stamina >= self.stats.max_stamina:
                await asyncio.sleep(self.stats.st_regen_tick)
                continue
            elif self.states.is_sprinting or self.states.jumped:
                await asyncio.sleep(self.stats.st_regen_delay)
                if self.states.is_sprinting or self.states.jumped:
                    continue
            
            if self.states.exhausted and not self.states.is_moving and not self.states.is_attacking:
                self.stats.stamina += self.stats.stamina_regen * self.stats.exhaustion_st_multiplier
            else:
                self.stats.stamina += self.stats.stamina_regen
                
            if self.stats.stamina >= self.stats.max_stamina:
                self.stats.stamina = self.stats.max_stamina
                self.states.exhausted = False
                
            self._update_stamina_bar()
            await asyncio.sleep(self.stats.st_regen_tick)
    
    def _start_st_loop(self) -> None:
        """Starts the stamina regen loop and stores it in a variable."""
        self._debug_msg("Starting Stamina Loop!", debug_handler=self._debug_logs.stamina)
        self._stamina_loop_task = self.page.run_task(self._stamina_regen_loop)
    
    async def _health_regen_loop(self) -> None:
        """Handles the natural health regen loop."""
        try:
            await asyncio.sleep(self.stats.hp_regen_delay)
            while not self.states.dead:
                if self.stats.health >= self.stats.max_health:
                    await asyncio.sleep(self.stats.hp_regen_tick)
                    continue
                
                self.stats.health += self.stats.health_regen
                if self.stats.health > self.stats.max_health:
                    self.stats.health = self.stats.max_health
                self._update_health_bar()
                await asyncio.sleep(self.stats.hp_regen_tick)
                
        except asyncio.CancelledError:
            self._update_health_bar()
    
    def _start_hp_loop(self) -> None:
        """Starts the health regen loop and stores it in a variable."""
        self._debug_msg("Starting Health Loop!", debug_handler=self._debug_logs.health)
        self._health_loop_task = self.page.run_task(self._health_regen_loop)
    
    # * === OTHER HELPERS ===
    def _start_loops(self) -> None:
        """Starts all the looping tasks."""
        self._start_animation_loop()
        self._start_movement_loop()
        self._start_st_loop()
        self._start_hp_loop()
    
    def _interrupt_action(self, cancel_temp_tasks: bool = True) -> bool:
        """
        Returns `False` if there are no interrupting actions occurring.
        """
        if (
            self.states.is_attacking
            or self.states.jumped
            or self.states.taking_damage
            or self.states.dead
        ): return True
        else:
            if cancel_temp_tasks: self._cancel_temp_tasks()
            return False
    
    def _get_jump_dy(self) -> int:
        """Returns the total jump distance."""
        _dist = float(self.stats.jump_distance)
        _str = self.stats.jump_strength
        return int(_dist * _str)
    
    def _get_dash_dx(self) -> int:
        """Returns the total dash distance."""
        _dist = float(self.stats.dash_distance)
        _str = self.stats.dash_strength
        return int(_dist * _str)