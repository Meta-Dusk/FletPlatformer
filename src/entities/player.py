import asyncio, inspect, time
import flet as ft
from pynput import keyboard
from dataclasses import dataclass
from enum import Enum

from entities.entity import Entity
from entities.features.entity_data import EntityStates, EntityStats, Factions, AnimConfig, SFXRegistry, AnimationState
from entities.projectile import ProjectileStats

from images import Sprite

from audio.audio_manager import AudioManager
from audio.sfx_data import SFXLibrary

from utilities.collisions import check_collision
from utilities.components import try_update
from utilities.keyboard_manager import HeldKeys
from utilities.physics import Velocity

from managers.projectiles import ProjectileManager

@dataclass
class PlayerData:
    name: str = "Unknown Player"
    width: ft.Number = 180
    height: ft.Number = 180

# TODO: Implement more player types
class PlayerType(Enum):
    """Available player types."""
    HERO_KNIGHT = PlayerData(name="Hero Knight")
    KING = PlayerData(name="King") # ! Not yet implemented

sfx = SFXLibrary()

class Player(Entity):
    """Handles the player's actions and states."""
    def __init__(
        self,
        page: ft.Page,
        audio_manager: AudioManager,
        sprite: Sprite,
        held_keys: HeldKeys,
        entity_list: list[Entity] = None,
        name: str = None,
        *,
        debug: bool = False,
        verbose_stamina: bool = False,
        type: PlayerType,
        stats: EntityStats,
        simple_revive: bool = True,
        restrict_movement: bool = True
    ) -> None:
        """The main setup for all player entities."""
        # ? Entity inherited class setup
        self._player_name = type.name.lower()
        self.name = type.value.name if name is None else name
        self._init_stats = stats
        
        super().__init__(
            sprite=sprite, name=self.name, page=page,
            audio_manager=audio_manager, faction=Factions.HUMAN,
            entity_list=entity_list, debug=debug, stats=self._init_stats,
            simple_revive=simple_revive, restrict_movement=restrict_movement
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
        
        self.last_attack_time: float = 0.0
        
        # --- NEW ANIMATION SYSTEM SETUP ---        
        # Define default animations (Subclasses should overwrite these)
        self.animations: dict[str, AnimConfig] = {
            "idle": AnimConfig(4, 0.075),
            "run": AnimConfig(6, 0.075),
            "fall": AnimConfig(1, 0.1),
        }
        
        # Animation State
        self.anim_timer: float = 0.0
        self.current_frame: int = 0
        self.current_anim_state: str | AnimationState = "idle"
        
        # ? Temp
        self.projectile_manager: ProjectileManager
    
    # * === ANIMATION TICKER ===
    def tick_animation(self, dt: float) -> bool:
        if self._tick_simple_revive(dt): return True
        
        if self.states.is_reviving: return False
        
        new_state = "idle"
        
        if self.states.dead:
            new_state = "death"
        elif self.states.taking_damage:
            new_state = "take-hit"
        elif self.states.is_attacking:
            new_state = f"attack-{self.states.attack_phase}"
            
        elif not self.on_ground:
            if self.velocity.dy > 0:
                new_state = "jump"
            else:
                new_state = "fall"
                self.states.jumped = False 
                
        elif self.states.is_moving:
            new_state = "run"
            
        did_frame_change = False
        
        # --- A. STATE SWITCH CHECK ---
        if new_state != self.current_anim_state:
            # Safety Valve for Attack Soft Lock
            if "attack" in self.current_anim_state and "attack" not in new_state:
                self.states.is_attacking = False
                self.states.dealing_damage = False
                self._modify_self_hitbox(reset=True)

            self.current_anim_state = new_state
            self.anim_timer = 0.0
            self.current_frame = 0
            did_frame_change = True
            
        # --- B. TIMER CHECK ---
        else:
            config = self.animations.get(self.current_anim_state)

            if config:
                # Exhaustion Logic
                duration = config.frame_duration
                if self.current_anim_state == "run" and self.states.exhausted:
                    duration = config.frame_duration / self.stats.exhaustion_modifier
                    
                self.anim_timer += dt
                
                if self.anim_timer >= duration:
                    
                    self.anim_timer = 0
                    self.current_frame += 1
                    
                    if self.current_frame >= config.frame_count:
                        if config.loop:
                            self.current_frame = 0
                        else:
                            self.current_frame = config.frame_count - 1
                            if not config.loop: self._on_animation_finish()
                        
                    did_frame_change = True

        # --- C. PROCESS FRAME ---
        if did_frame_change:
            # 1. Trigger SFX
            events = self.sfx_registry.get(self.current_anim_state, self.current_frame)
            
            for event in events:
                self._play_sfx(event.sfx, event.volume)
                    
            self._update_sprite_src()
            return True
        return False
    
    @property
    def dash_velocity(self) -> ft.Number:
        """Returns the total dash velocity."""
        return self.stats.dash_distance * self.stats.dash_strength
    
    @property
    def jump_velocity(self) -> ft.Number:
        """Returns the total jump velocity."""
        return self.stats.jump_distance * self.stats.jump_strength
    
    # * === DAMAGE DETECTION ===
    def _detect_damage(self):
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
                        self.take_damage(*self._calculate_damage())
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
    
    async def _living_loop(self) -> None:
        """The main loop that only ticks if entity is alive."""
        while not self.states.dead:
            pass
    
    async def _movement_loop(self) -> None:
        """Handles player movements."""
        MV_DELAY: float = 0.05
        dx: ft.Number = 0
        while not self.states.dead:
            
            await self._detect_attack_hits()
            self._detect_damage()
            
            # --- LANDING LOGIC ---
            # 1. Detect Landing: We were falling, but physics says we are now on ground
            if self.states.is_falling and self.on_ground:
                self._play_sfx_list(self.landing_sfx_list)
                self.states.is_falling = False
                self.states.jumped = False
                
            # 2. Detect Falling: We are in the air (Jumped or walked off ledge)
            elif not self.on_ground: self.states.is_falling = True
            
            if (
                not self.page.window.focused or
                self.states.is_attacking or
                self.states.taking_damage or
                self.states.disable_movement
            ):
                self.velocity.dx = 0
                await asyncio.sleep(MV_DELAY)
                continue
            
            is_shift_held = keyboard.Key.shift in self.held_keys
            if is_shift_held and self.stats.stamina > 0 and not self.states.exhausted:
                step = self.stats.movement_speed * self.stats.sprint_mult
            else:
                if self.states.exhausted:
                    step = self.stats.movement_speed * self.stats.exhaustion_modifier
                else:
                    step = self.stats.movement_speed
            
            # Reset horizontal velocity when not dashing
            if not self.states.is_dashing: dx = 0
            
            if 'a' in self.held_keys: dx -= step
            if 'd' in self.held_keys: dx += step
            
            if (
                ('a' in self.held_keys or 'd' in self.held_keys)
                and 'c' in self.held_keys
            ):
                dx += self.dash(dx)
            
            def on_movement() -> None:
                """Stamina check and update when sprinting."""
                self.states.is_sprinting = is_shift_held
                if self.states.is_sprinting and self.stats.stamina > 0:
                    self.stats.stamina -= self.stats.st_usage_tick
                    self._update_stamina_bar()
                elif self.stats.stamina <= 0:
                    self.states.exhausted = True
                    self.stats.stamina = 0
            
            self._check_movement(
                dx, on_movement=on_movement,
                # on_direction_changed=lambda: self._play_sfx_list(self.looking_away_sfx_list)
            )
            
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
    def attack_ranged(self) -> None:
        direction = self._get_facing_direction()
        
        bomb_stats = ProjectileStats(
            velocity=Velocity(dx=5.0, dy=4.0),
            gravity=9.8,
            damage=10,
            collides_with_map=True,
            bounciness=0.25,
            friction=25.0,
            lifespan=5.0,
            width=100,
            height=100,
            offset=ft.Offset(0, 0.35),
            fly_anim=AnimConfig(frame_count=3, frame_duration=0.1, loop=True),
            explode_anim=AnimConfig(frame_count=19, frame_duration=0.08, loop=False),
        )
        
        self.projectile_manager.spawn_projectile(
            start_x=self.stack.left + self.stack.width / 2,
            start_y=(self.stack.bottom + self.stack.height / 2) - 50,
            direction=direction,
            owner=self,
            stats=bomb_stats,
            src="images/enemies/goblin/projectile_0.png"
        )
    
    def death(self) -> None:
        """Cancels all running tasks, and plays the death animation."""
        if not super().death(): return
        self._reset_states(EntityStates(dead=True))
        self._cancel_loop_tasks()
        if self.on_death: self.on_death()
        self._toggle_atk_hb_border()
    
    def dash(self, dx: float) -> ft.Number:
        """Player dash action. Returns velocity amount."""
        # Checks
        if self._has_dashed: return 0
        if self.stats.stamina <= 0: return 0
        elif (self.stats.stamina - self.stats.dash_st_cost) <= 0: return 0
        
        # Costs and states
        self._has_dashed = True
        self.states.invincible = True
        self.states.is_dashing = True
        self.stats.stamina -= self.stats.dash_st_cost
        self._update_stamina_bar()
        self._apply_tint(ft.Colors.PURPLE)
        self._play_sfx(sfx.whoosh.motion, 0.5)
        
        direction = 1 if dx > 0 else -1
        self._debug_msg(f"Dashing to the {"left" if direction < 0 else "right"}!", debug_handler=self._debug_logs.dash)
        
        async def timer() -> None:
            """Handles the dash cooldown."""
            await asyncio.sleep(self.stats.dash_duration)
            self._reset_tint()
            self.states.invincible = False
            self.states.is_dashing = False
            self.velocity.dx = 0
            await asyncio.sleep(self.stats.dash_cooldown - self.stats.dash_duration)
            self._has_dashed = False
            self.dash_indicator.color = None
            try_update(self.dash_indicator)
            
        self.page.run_task(timer)
        self.dash_indicator.color = ft.Colors.with_opacity(0.75, ft.Colors.GREY)
        try_update(self.dash_indicator)
        
        return self.dash_velocity * direction
    
    def jump(self) -> None:
        """Player jump action."""
        if not self.on_ground or self._interrupt_action(): return
        elif self.stats.stamina <= 0: return
        elif (self.stats.stamina - self.stats.jump_st_cost) <= 0: return
        elif self.states.exhausted: return
        
        self.stats.stamina -= self.stats.jump_st_cost
        self._update_stamina_bar()
        
        self.velocity.dy = self.jump_velocity
        
        self.states.jumped = True
        self.on_ground = False
    
    def attack(self) -> None:
        """Player attack. Combo cycles: 1 -> 2 -> 1."""
        if not super().attack(): return
        
        direction = self._get_facing_direction()
        
        if 'a' in self.held_keys:
            if direction == 1:
                direction = -1
        elif 'a' in self.held_keys:
            if direction == -1:
                direction = 1
        
        self._flip_sprite_x(direction)
        
        current_time = time.time()
        COMBO_WINDOW = 1.0 # Seconds allowed between hits to keep combo
        
        # 1. Combo Logic
        # If too much time passed, or we jumped (air attacks usually reset), reset to 1
        if (current_time - self.last_attack_time > COMBO_WINDOW) or self.states.jumped:
            self.states.attack_phase = 1
        else:
            self.states.attack_phase += 1
            
        # Cycle Logic (1 -> 2 -> 1)
        if self.states.attack_phase > 2: 
            self.states.attack_phase = 1
            
        # self._debug_msg(f"Attacking! Phase: {self.states.attack_phase}")
        
        # 2. Set State
        self.states.is_attacking = True
        self.last_attack_time = current_time
        
    def take_damage(self, damage_amount: float, is_crit: bool = False) -> None:
        """Decrease player's health with logic."""
        if not super().take_damage(damage_amount, is_crit): return
        
        if self.states.is_attacking:
            self.states.is_attacking = False
            self.states.dealing_damage = False
            self._toggle_atk_hb_border()
            self._modify_self_hitbox(reset=True)
            
        self._apply_tint(ft.Colors.RED)
        
        if self.stats.health <= 0: self.death()
    
    async def heal(self, heal_amount: float, overheal: bool = False) -> None:
        """Heals the player."""
        if not super().heal(heal_amount, overheal): return
        self.states.is_healing = True
        self._update_health_bar()
        self._apply_tint(ft.Colors.GREEN)
        await asyncio.sleep(self.stats.healing_delay)
        self._reset_tint()
        self.states.is_healing = False
    
    def revive(self) -> None:
        """Revives the player."""
        if not super().revive(): return
    
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
        self._start_movement_loop()
        self._start_st_loop()
        self._start_hp_loop()
    
    def _interrupt_action(self) -> bool:
        """
        Returns `False` if there are no interrupting actions occurring.
        """
        if (
            self.states.is_attacking
            or self.states.jumped
            or self.states.taking_damage
            or self.states.dead
        ): return True
        else: return False