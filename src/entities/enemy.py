import asyncio, random
import flet as ft
from dataclasses import dataclass
from enum import Enum

from entities.entity import Entity
from entities.features.entity_data import EntityStates, EntityStats, Factions
from images import Sprite
from audio.audio_manager import AudioManager
from audio.sfx_data import SFXLibrary
from utilities.tasks import attempt_cancel
from utilities.collisions import is_in_x_range
from utilities.components import try_update, await_for_dur

sfx = SFXLibrary()

@dataclass
class EnemyData:
    name: str = "Unknown Enemy"
    width: ft.Number = 150
    height: ft.Number = 150
    melee_range: int = 100

class EnemyType(Enum):
    """Available enemy types."""
    # FLYING_EYE = EnemyData("Flying Eye")
    GOBLIN = EnemyData("Gobby", melee_range=120)
    # MUSHROOM = EnemyData("Mushy")
    # SKELETON = EnemyData("Skelly")

# TODO: Finish the Enemy class
# TODO: Add a revive method to the Enemy class
class Enemy(Entity):
    """Handles an enemy's actions and states."""
    def __init__(
        self, type: EnemyType, page: ft.Page,
        audio_manager: AudioManager, target: Entity = None,
        name: str = None, entity_list: list[Entity] = None,
        *, debug: bool = False
    ):
        """
        Important setup for the class. Starts setup with the
        parent class first before its internal setup.
        """
        # ? Entity inherited class setup
        self._enemy_name = type.name.lower()
        _sprite = Sprite(
            src=f"images/enemies/{self._enemy_name}/idle_0.png",
            width=type.value.width, height=type.value.height
        )
        self.name = type.value.name if name is None else name
        
        # Random stats
        rnd_health_range = (10, 20)
        mv_speed_min = 10
        rnd_health = random.randint(*rnd_health_range)
        k = rnd_health_range[1] * mv_speed_min
        rnd_mv_speed = round(k / rnd_health)
        self._init_stats = EntityStats(
            movement_speed=rnd_mv_speed,
            health=rnd_health, max_health=rnd_health
        )
        
        super().__init__(
            sprite=_sprite, name=self.name, page=page,
            audio_manager=audio_manager, faction=Factions.NONHUMAN,
            entity_list=entity_list, debug=debug, stats=self._init_stats
        )
        
        # ? Internal class setup
        self.type = type
        self.target = target
        self._handler_str = self.name
        self.is_idling: bool = False
        self.melee_range: int = type.value.melee_range
        self._rnd_dx: int = 0
        self._make_atk_hitbox(
            p1_r_left=-15, p1_width=180, p1_height=100,
            p2_r_left=70, p2_width=140, p2_height=80
        )
        self._make_self_hitbox(width=70, height=75, r_left=40)
    
    # * === LOOPING ANIMATIONS ===
    async def _animation_loop(self):
        """Handles an enemy's different animation loops."""
        frame: int = 0
        RUNNING_FRAMES: int = 7
        RUNNING_FRAME_DURATION: float = 0.075
        IDLE_FRAMES: int = 3
        FOOTSTEPS_VOLUME: float = 0.2
        
        while not self.states.dead:
            # Give way to other animations
            if self.states.is_attacking or self.states.taking_damage or self.states.dead:
                await asyncio.sleep(self._LOGIC_DELAY)
                continue
            
            # Running animation
            if self.states.is_moving:
                if frame > RUNNING_FRAMES: frame = 0
                await asyncio.sleep(RUNNING_FRAME_DURATION)
                self.sprite.change_src(self._get_spr_path("run", frame))
                if frame == 2: self._play_sfx(sfx.footsteps.footstep_grass_1, FOOTSTEPS_VOLUME)
                if frame == 5: self._play_sfx(sfx.footsteps.footstep_grass_1, FOOTSTEPS_VOLUME)
             
             # Idle animation
            else:
                if frame > IDLE_FRAMES: frame = 0
                await asyncio.sleep(self._LOGIC_DELAY)
                self.sprite.change_src(self._get_spr_path("idle", frame))
            
            frame += 1
    
    # * === CUSTOM MOVEMENT LOOP ===
    async def _movement_loop(self):
        """Handles the goblin's simple AI."""
        # Announce if goblin is spawned in the scene (sfx + fade in)
        await asyncio.sleep(self._LOGIC_DELAY)
        self._play_sfx(sfx.enemy.goblin_cackle)
        self.stack.opacity = 1
        try_update(self.stack)
        await await_for_dur(self.stack.animate_opacity)
        
        while not self.states.dead:
            if self.states.disable_movement:
                self.states.is_moving = False
                await asyncio.sleep(self._LOGIC_DELAY)
                continue
            
            dx, dy = 0, 0
            
            # ? Chase Target (if out of range)
            if not self._is_target_in_range():
                if self.target and not self.target.states.dead:
                    self._debug_msg(f"Chasing {self.target.name}", end=" -> ", debug_handler=self._debug_logs.movement)
                    if self._get_center_point(self.target) > self._get_center_point(self):
                        if self.target.states.dealing_damage:
                            dx = -self.stats.movement_speed
                        else: dx = self.stats.movement_speed
                    elif self._get_center_point(self.target) < self._get_center_point(self):
                        if self.target.states.dealing_damage:
                            dx = self.stats.movement_speed
                        else: dx = -self.stats.movement_speed
                    self.is_idling = False
                else: self.is_idling = True
                
            else: # ? Attack Target (if in range)
                if self.target and not self.target.states.dead:
                    self._debug_msg("Attacking target", debug_handler=self._debug_logs.attack)
                    
                    # Predict target if target is jumping
                    if self.target.states.jumped:
                        if self.target.states.is_attacking:
                            self.states.attack_phase = 0
                        else: self.states.attack_phase = 1
                        if (
                            self._get_center_point(self.target) > self._get_center_point(self) or
                            self._get_center_point(self.target) < self._get_center_point(self)
                        ):
                            self._flip_char(dx)
                    
                    self.attack()
                    await asyncio.sleep(1)
                    continue
                else: self.is_idling = True
            
            # ? Simple idle mechanic
            if self.is_idling:
                if self._rnd_dx == 0:
                    # 10% chance of attempting random movement when idle
                    if random.randint(1, 10) > 9:
                        self._rnd_dx = random.randint(-1, 1) * self.stats.movement_speed
                else:
                    # 30% chance of staying still when idle
                    if random.randint(1, 10) > 7: self._rnd_dx = 0
                    else: dx += self._rnd_dx
            
            self._check_movement(dx, dy)
            if self.states.is_moving:
                self.states.dealing_damage = False
                try_update(self.stack)
            await asyncio.sleep(self._LOGIC_DELAY)
        
    
    # * === ONE-SHOT ANIMATIONS ===
    async def _attack_anim(self):
        """Handles the enemy's attack animations with combos."""
        prefix = f"attack-{self.states.attack_phase}"
        mod_atk_delay = self.stats.attack_frame_delay * 1.5
        FRAMES = 7
        
        for frame in range(FRAMES + 1):
            await asyncio.sleep(mod_atk_delay if self.states.stun_immune else self.stats.attack_frame_delay)
            if self.states.attack_phase == 1:
                # 50% chance of parry
                if frame == 2 and random.randint(1, 2) > 1:
                    self._apply_tint(ft.Colors.YELLOW)
                    self.states.stun_immune = True
                elif frame == 5:
                    self._reset_tint()
                    self.states.stun_immune = False
                elif frame == 6:
                    self._modify_self_hitbox(width=80, height=80, r_left=10)
            elif self.states.attack_phase == 2:
                if frame == 0: self._modify_self_hitbox(r_left=30)
                elif frame == 1: self._modify_self_hitbox(r_left=0)
                elif frame == 2: self._modify_self_hitbox(r_left=-5, height=60)
                elif frame in {2, 3, 4}:
                    if self.target.states.is_attacking: await asyncio.sleep(0.05)
                elif frame == 5: self._modify_self_hitbox(r_left=50, height=60)
                
            if frame == 5: self._play_sfx(sfx.enemy.boggart_hya)
            elif frame == 6:
                self.states.dealing_damage = True
                self._toggle_atk_hb_border()
            elif frame == 7:
                self.states.dealing_damage = False
                self._toggle_atk_hb_border()
            self.sprite.change_src(self._get_spr_path(prefix, frame))
            
        self._modify_self_hitbox(reset=True)
        self.states.is_attacking = False
        self._attack_task = None
        self._toggle_atk_hb_border()
    
    async def _death_anim(self):
        """Handles the enemy's death animation."""
        FRAMES = 3
        self._update_health_bar()
        self._play_sfx(sfx.enemy.goblin_scream)
        self._play_sfx(sfx.impacts.flesh_impact_2)
        
        for frame in range(FRAMES + 1):
            await asyncio.sleep(self._LOGIC_DELAY)
            self.sprite.change_src(self._get_spr_path("death", frame))
            
        self.states.revivable = True
    
    async def _take_hit_anim(self, play_animation: bool = True):
        """Handles the enemy's taking damage animation."""
        FRAMES: int = 3
        
        for frame in range(FRAMES + 1):
            await asyncio.sleep(self._LOGIC_DELAY)
            if play_animation: self.sprite.change_src(self._get_spr_path("take-hit", frame))
            if frame == 1:
                self._update_health_bar()
                self._play_sfx(sfx.enemy.goblin_hurt)
                if self.target.states.attack_phase == 1: self._play_sfx(sfx.impacts.flesh_impact_1)
                elif self.target.states.attack_phase == 2: self._play_sfx(sfx.impacts.axe_hit_flesh)
            if frame == 2: self._knockback_self(self.target)
            
        self.states.taking_damage = False
        self._take_hit_task = None
        self._reset_tint()
    
    # * === CLEANUP ===
    def remove_selves(self):
        """Removes `self` from `stage` and `_entity_list`."""
        entity_stack = self._get_parent()
        
        msg_1 = "Attempting to remove 'self' from 'entity_stack':"
        self._debug_msg(f"{msg_1} {len(entity_stack.controls)} -> ", end="", debug_handler=self._debug_logs.cleanup)
        if self.stack in entity_stack.controls:
            entity_stack.controls.remove(self.stack)
            try_update(entity_stack)
        self._debug_msg(len(entity_stack.controls), include_handler=False, debug_handler=self._debug_logs.cleanup)
        
        msg_2 = "Attempting to remove 'self' from '_entity_list':"
        self._debug_msg(f"{msg_2} {len(self._entity_list)} -> ", end="", debug_handler=self._debug_logs.cleanup)
        if self._entity_list is not None and self in self._entity_list: self._entity_list.remove(self)
        self._debug_msg(len(self._entity_list), include_handler=False, debug_handler=self._debug_logs.cleanup)
    
    # * === CALLABLE PLAYER ACTIONS/EVENTS ===
    def __call__(self, *, start_loops: bool = True, center_spawn: bool = True):
        """
        Returns the `Stack` control, and starts the movement and
        animation loops. Set `center_spawn` to make the enemy spawn
        random across the x-axis.
        """
        if not center_spawn:
            width = self.sprite.width
            new_left = random.randint(width, int(self.page.width)) - width
            self.stack.left = new_left
        if start_loops:
            self._start_animation_loop()
            self._start_movement_loop()
        return super().__call__()
    
    async def death(self):
        """Cancels all running tasks, and plays the death animation."""
        if not super().death(): return
        # ? Death states and stats
        self._reset_states(EntityStates(dead=True))
        self._reset_stats(self._init_stats)
        self._debug_msg(f"{self.name} has died!", debug_handler=self._debug_logs.death)
        self._update_health_bar()
        self._apply_tint(ft.Colors.RED)
        
        # ? Animation handling
        attempt_cancel(self._animation_loop_task)
        self._cancel_temp_tasks()
        await self._death_anim()
        self._toggle_atk_hb_border()
        self.states.revivable = True # ? Possibility of revival soon
        await asyncio.sleep(1) # A bit of delay before despawning
        
        # ? Despawn and cleanup
        self.states.revivable = False
        self.stack.opacity = 0
        try_update(self.stack)
        await asyncio.sleep(self.stack.animate_opacity.duration / 1000)
        self._cancel_loop_tasks()
        self._cleanup_ready = True
        
    def attack(self):
        """
        Enemy attack. Melee combo cycles: 1 -> 2 -> 1.
        Ranged attack based on distance to player.
        """
        if not super().attack(): return
        self.states.attack_phase += 1
        if self.states.attack_phase > 2: self.states.attack_phase = 1
        self._debug_msg(f"Attacking! Phase: {self.states.attack_phase}", debug_handler=self._debug_logs.attack)
        self.states.is_attacking = True
        self.states.dealing_damage = False
        self._attack_task = self.page.run_task(self._attack_anim)
    
    def take_damage(self, damage_amount: float, is_crit: bool = False):
        """Decrease enemy's health with logic. Returns `True` if entity has died."""
        if not super().take_damage(damage_amount, is_crit): return False
        self.states.is_moving = False
        
        if self.states.is_attacking:
            if self.states.stun_immune and self.stats.health > 0:
                self._play_sfx(sfx.impacts.shield_block_shortsword, 1.0)
            elif not self.states.stun_immune:
                attempt_cancel(self._attack_task)
                self.states.is_attacking = False
                self.states.dealing_damage = False
                self._toggle_atk_hb_border()
                self._modify_self_hitbox(reset=True)
                
        self._apply_tint(ft.Colors.RED)
        if self.stats.health <= 0:
            self.page.run_task(self.death)
            return True
        else:
            if self._take_hit_task: attempt_cancel(self._take_hit_task)
            if self.states.stun_immune:
                self._take_hit_task = self.page.run_task(self._take_hit_anim, False)
            else: self._take_hit_task = self.page.run_task(self._take_hit_anim)
            return False
    
    # * === OTHER HELPERS ===
    def _is_target_in_range(self, threshold: float = None):
        """Checks if the specifically targeted `Entity` is in range."""
        if self.target is None: return False
        
        # We assume the target (i.e., Player) has a sprite and stack
        p_w = self.target.sprite.width
        
        return is_in_x_range(
            entity1_stack=self.stack,
            entity1_w=self.sprite.width,
            entity2_stack=self.target.stack,
            entity2_w=p_w,
            threshold=self.melee_range if threshold is None else threshold
        )
        
    # * === COMPONENT METHODS ===
    def _make_stack(self):
        stack = super()._make_stack()
        rnd_duration = random.randint(1000, 2000)
        stack.animate_opacity = ft.Animation(rnd_duration, ft.AnimationCurve.EASE_IN_OUT)
        stack.opacity = 0
        return stack
