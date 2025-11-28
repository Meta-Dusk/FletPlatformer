import asyncio, random
import flet as ft
from pynput import keyboard

from entities.entity import Entity, EntityStates, EntityStats, Factions
from images import Sprite
from audio.audio_manager import AudioManager
from audio.sfx_data import SFXLibrary
from utilities.keyboard_manager import held_keys
from utilities.tasks import attempt_cancel
from utilities.collisions import check_collision

sfx = SFXLibrary()

class Player(Entity):
    """Handles the player's actions and states."""
    def __init__(
        self, page: ft.Page, audio_manager: AudioManager,
        held_keys: set = set(), entity_list: list[Entity] = None,
        *, debug: bool = False
    ):
        sprite = Sprite(
            src="images/player/idle_0.png", width=180, height=180,
            offset=ft.Offset(0, 0.225)
        )
        self.name = "Hero Knight"
        super().__init__(
            sprite=sprite, name=self.name, page=page,
            audio_manager=audio_manager, faction=Factions.HUMAN,
            entity_list=entity_list, debug=debug
        )
        self.held_keys = held_keys
        self._handler_str = "Player"
        self._jump_task: asyncio.Task = None
        self._attack_task: asyncio.Task = None
        self._take_hit_task: asyncio.Task = None
        self._animation_loop_task: asyncio.Task = None
        self._make_atk_hitbox(
            p1_r_left=70, p1_width=100, p1_height=150,
            p2_r_left=120, p2_width=140, p2_height=160
        )
        self._make_self_hitbox(width=95, height=110, r_left=55)
    
    # * === LOOPING ANIMATIONS ===
    async def _animation_loop(self):
        """Handles the player's different animation loops."""
        index: int = 0
        while not self.states.dead:
            # Give way to other animations
            if self._interrupt_action():
                await asyncio.sleep(0.1) # ? Important logic delay
                continue
            
            # Falling animation
            if self.states.is_falling:
                if index > 2: index = 0
                await asyncio.sleep(0.1)
                self.sprite.change_src(self._get_spr_path("fall", index))
            
            # Running animation
            if self.states.is_moving and not self.states.is_falling:
                if index > 7: index = 0
                wait_time = 0.05 if self.states.sprint else 0.075
                await asyncio.sleep(wait_time)
                self.sprite.change_src(self._get_spr_path("run", index))
                if index == 2:
                    self._play_sfx(sfx.armor.rustle_2, 0.2)
                    self._play_sfx(sfx.footsteps.footstep_grass_1, 0.2)
                if index == 5:
                    self._play_sfx(sfx.armor.rustle_3, 0.2)
                    self._play_sfx(sfx.footsteps.footstep_grass_2, 0.2)
                
            # Idle animation
            elif not self.states.is_moving and not self.states.is_falling:
                if index > 10: index = 0
                await asyncio.sleep(0.075)
                self.sprite.change_src(self._get_spr_path("idle", index))
            
            index += 1
    
    def _start_animation_loop(self):
        """Starts the animation loop and stores it in a variable."""
        self._animation_loop_task = self.page.run_task(self._animation_loop)
    
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
                        self._debug_msg(f"Hit by {entity.name}!")
                        await self.take_damage(entity.stats.attack_damage)
                        self._knockback_self(entity)
                        return
    
    async def _detect_attack_hits(self):
        """
        Checks if the Player's active attack hitbox collides with any enemy.
        """
        if not self.states.dealing_damage or not self._entity_list: return
        
        # ... (Get Active Hitbox logic) ...
        hb_index = self.states.attack_phase - 1
        active_hb = self._atk_hitboxes[hb_index]
        
        # Player Weapon Global Coords
        w_left = self.stack.left + (active_hb.left or 0)
        w_bottom = self.stack.bottom + (active_hb.bottom or 0)
        
        for enemy in self._entity_list:
            if enemy.faction == Factions.HUMAN or enemy.states.dead: continue
            
            # 1. Get Enemy's Body Rect (Using their new Hitbox!)
            e_left, e_bottom, e_w, e_h = enemy._get_self_global_rect()

            if check_collision(
                r1_left=w_left, r1_bottom=w_bottom, r1_w=active_hb.width, r1_h=active_hb.height, # Player Weapon
                r2_left=e_left, r2_bottom=e_bottom, r2_w=e_w, r2_h=e_h # Enemy Body
            ):
                self._debug_msg(f"Hit enemy: {enemy.name}")
                self.page.run_task(enemy.take_damage, self.stats.attack_damage)
    
    # * === CUSTOM MOVEMENT LOOP ===
    async def _movement_loop(self):
        """Handles player movements."""
        while True:
            await self._detect_attack_hits()
            await self._detect_damage()
            if self.states.dead or self.states.disable_movement:
                self.states.is_moving = False
                await asyncio.sleep(0.1)
                continue
            
            is_shift_held = keyboard.Key.shift in self.held_keys
            # is_ctrl_held = keyboard.Key.ctrl_l in keyboard_manager.held_keys # ? Enable if needed
            if self.page.window.focused and \
            (not self.states.is_attacking and not self.states.taking_damage):
                step = self.stats.movement_speed * 2 if is_shift_held else self.stats.movement_speed
                dx, dy = 0, 0
                
                # if 'w' in keyboard_manager.held_keys: dy -= step # ? Use for flying upwards
                # if 's' in keyboard_manager.held_keys: dy += step # ? Use for flying downwards
                if 'a' in self.held_keys: dx -= step
                if 'd' in self.held_keys: dx += step
                if (self.stack.left + dx) <= 0 or (self.stack.left + dx + self.sprite.width) >= self.page.width: dx = 0
                
                # ? Movement
                def primary_callback(): self.states.sprint = True if is_shift_held else False
                
                self._check_movement(
                    dx, dy, primary_callback=primary_callback,
                    secondary_callback=lambda: self._play_sfx(sfx.armor.rustle_1)
                )
                
            else:
                # ? Reset state if doing nothing or window not focused
                self.states.is_moving = False
                self.states.sprint = False
            
            # ? Grounding
            if self.stack.bottom < self.ground_level:
                self.stack.bottom += 10
                if self.stack.bottom > self.ground_level: self.stack.bottom = 0
                
            # ? Gravity
            elif self.stack.bottom > self.ground_level and not self.states.jumped:
                self.states.is_falling = True
                self.stack.bottom -= 25
                if self.stack.bottom <= self.ground_level:
                    self._play_sfx(sfx.player.jump_landing)
                    self._play_sfx(sfx.player.exhale)
                    self._play_sfx(sfx.impacts.landing_on_grass)
                
            elif self.stack.bottom == self.ground_level: self.states.is_falling = False
            if self.states.is_moving or self.states.is_falling: self._safe_update(self.stack)
            await asyncio.sleep(0.05) # ? Delay for logic just in case
    
    # * === ONE-SHOT ANIMATIONS ===
    async def _revive_anim(self):
        """Handles the player's revival animation."""
        index = 10
        self._play_sfx(sfx.magic.strike)
        while index >= 0:
            await asyncio.sleep(0.1)
            if index == 5: self._play_sfx(sfx.armor.rustle_3)
            self.sprite.change_src(self._get_spr_path("death", index))
            index -= 1
    
    async def _jump_anim(self):
        """Handles the player's jump animation."""
        self._play_sfx(sfx.cloth.rough_rustle)
        self._play_sfx(sfx.player.inhale_exhale_short)
        for i in range(3):
            await asyncio.sleep(0.1)
            if self.states.is_attacking: continue # ? Skips animation if attacking mid-air
            self.sprite.change_src(self._get_spr_path("jump", i))
        await asyncio.sleep(self.stats.jump_air_time)
        self.states.jumped = False
        self._jump_task = None
    
    async def _attack_anim(self):
        """Handles the player's attack animations with combos."""
        prefix = "attack-main" if self.states.attack_phase == 1 else "attack-secondary"
        for i in range(7):
            await asyncio.sleep(0.1)
            if self.states.attack_phase == 1: # Upward slash
                if i == 1: self._modify_self_hitbox(r_left=40)
                if i == 2: # TODO: Optimize audio by combining into one SFX
                    self._play_sfx(sfx.sword.fast_woosh)
                    self._play_sfx(sfx.player.small_grunt)
            elif self.states.attack_phase == 2: # Downward slash
                if i == 1:
                    self._play_sfx(sfx.sword.ting)
                    self._play_sfx(sfx.player.grunt)
                elif i == 3:
                    self._modify_self_hitbox(r_left=100)
                    self._play_sfx(sfx.impacts.landing_on_grass)
            if i == 3: # Either attack
                self.states.dealing_damage = True
                self._toggle_atk_hb_border()
            elif i == 5:
                self.states.dealing_damage = False
                self._toggle_atk_hb_border()
            self.sprite.change_src(self._get_spr_path(prefix, i))
        self._modify_self_hitbox(reset=True)
        self.states.is_attacking = False
        self._attack_task = None
        self._toggle_atk_hb_border()
    
    async def _death_anim(self):
        """Handles the player's death animation."""
        death_sfx = [sfx.player.death_1, sfx.player.death_2]
        for i in range(11):
            await asyncio.sleep(0.1)
            if i == 3: self._play_sfx(random.choice(death_sfx))
            if i == 4: self._play_sfx(sfx.cloth.clothes_drop)
            if i == 5: self._play_sfx(sfx.armor.hit_soft)
            if i == 6: 
                self._play_sfx(sfx.item.keys_drop)
                self._play_sfx(sfx.sword.blade_drop)
            self.sprite.change_src(self._get_spr_path("death", i))
        self.states.revivable = True
    
    async def _take_hit_anim(self):
        """Handles the player's taking damage animation."""
        for i in range(4):
            await asyncio.sleep(0.1)
            if i == 1: self._play_sfx(sfx.player.grunt_hurt)
            self.sprite.change_src(self._get_spr_path("take-hit", i))
        self.states.taking_damage = False
        self._take_hit_task = None
    
    # * === CALLABLE PLAYER ACTIONS/EVENTS ===
    async def death(self):
        """Cancels all running tasks, and plays the death animation."""
        if not super().death(): return
        self._debug_msg(f"{self.name} has died!")
        self._reset_states(EntityStates(dead=True))
        self._reset_stats(EntityStats(health=0))
        await self._update_health_bar()
        
        attempt_cancel(self._animation_loop_task)
        self._cancel_temp_tasks()
        await self._death_anim()
        self._toggle_atk_hb_border()
    
    def jump(self):
        """Play jump action."""
        if self.stack.bottom != 0 or self._interrupt_action(): return
        self.stack.bottom += self._get_jump_dy()
        self._safe_update(self.stack)
        self.states.jumped = True
        self._jump_task = self.page.run_task(self._jump_anim)
    
    def attack(self):
        """Player attack. Combo cycles: 1 -> 2 -> 1."""
        if not super().attack(): return
        self.states.attack_phase += 1
        if self.states.attack_phase > 2 or self.states.jumped: self.states.attack_phase = 1
        self._debug_msg(f"Attacking! Phase: {self.states.attack_phase}")
        self.states.is_attacking = True
        self._attack_task = self.page.run_task(self._attack_anim)
        
    async def take_damage(self, damage_amount: float):
        """Decrease player's health with logic."""
        if not super().take_damage(): return
        self.stats.health -= damage_amount
        self._debug_msg(f"Took damage: {damage_amount}, health is now: {self.stats.health}")
        self.states.taking_damage = True
        if (self.states.is_attacking and self.states.jumped) or self.states.is_attacking:
            attempt_cancel(self._attack_task)
            self.states.is_attacking = False
            self.states.dealing_damage = False
            self._toggle_atk_hb_border()
            self._modify_self_hitbox(reset=True)
            self._safe_update(self.stack)
        if self.stats.health <= 0: await self.death()
        else: self._take_hit_task = self.page.run_task(self._take_hit_anim)
        await self._update_health_bar()
    
    async def revive(self):
        if not super().revive(): return
        self.states.revivable = False
        self._debug_msg(f"Reviving: {self.name}")
        await self._revive_anim()
        self._reset_states()
        self._reset_stats()
        attempt_cancel(self._movement_loop_task)
        await self._update_health_bar()
        self._start_loops()
    
    def __call__(self, start_loops: bool = True):
        """
        Returns the `Stack` control, and starts the movement and
        animation loops.
        """
        if start_loops: self._start_loops()
        return super().__call__()
    
    # * === OTHER HELPERS ===
    def _cancel_temp_tasks(self):
        """Cancels all running temporary tasks."""
        tasks = [
            self._jump_task,
            self._attack_task,
            self._take_hit_task
        ]
        for task in tasks: attempt_cancel(task)
        
    def _start_loops(self):
        self._start_animation_loop()
        self._start_movement_loop()
    
    def _interrupt_action(self):
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
            self._cancel_temp_tasks()
            return False
    
    def _get_jump_dy(self):
        """Returns the total jump distance."""
        _dist = float(self.stats.jump_distance)
        _str = self.stats.jump_strength
        return int(_dist * _str)
    