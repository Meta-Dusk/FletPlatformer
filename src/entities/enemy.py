import asyncio, random
import flet as ft
from dataclasses import dataclass
from enum import Enum

from entities.entity import Entity, EntityStates, EntityStats, Factions
from images import Sprite
from audio.audio_manager import AudioManager
from audio.sfx_data import SFXLibrary
from utilities.tasks import attempt_cancel
from utilities.collisions import is_in_x_range

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
        self._attack_task: asyncio.Task = None
        self._take_hit_task: asyncio.Task = None
        self._animation_loop_task: asyncio.Task = None
        self.is_idling: bool = False
        self.melee_range: int = type.value.melee_range
        self._cached_player_stack = None
        self._damage_detection_task: asyncio.Task = None
        self._rnd_dx: int = 0
        self._make_atk_hitbox(
            p1_r_left=-15, p1_width=180, p1_height=100,
            p2_r_left=70, p2_width=140, p2_height=80
        )
        self._make_self_hitbox(width=70, height=75, r_left=40)
    
    # * === LOOPING ANIMATIONS ===
    async def _animation_loop(self):
        """Handles an enemy's different animation loops."""
        index: int = 0
        while not self.states.dead:
            # Give way to other animations
            if self.states.is_attacking or self.states.taking_damage or self.states.dead:
                await asyncio.sleep(0.1) # ? Important logic delay
                continue
            
            # Running animation
            if self.states.is_moving:
                if index > 7: index = 0
                await asyncio.sleep(0.075)
                self.sprite.change_src(self._get_spr_path("run", index))
                if index == 2: self._play_sfx(sfx.footsteps.footstep_grass_1, 0.2)
                if index == 5: self._play_sfx(sfx.footsteps.footstep_grass_1, 0.2)
             
             # Idle animation
            else:
                if index > 3: index = 0
                await asyncio.sleep(0.1)
                self.sprite.change_src(self._get_spr_path("idle", index))
            
            index += 1
    
    def _start_animation_loop(self):
        """Starts the animation loop and stores it in a variable."""
        self._animation_loop_task = self.page.run_task(self._animation_loop)
    
    # * === CUSTOM MOVEMENT LOOP ===
    async def _movement_loop(self):
        """Handles the enemy's movements."""
        await asyncio.sleep(0.1)
        self._play_sfx(sfx.enemy.goblin_cackle)
        self.stack.opacity = 1
        self._safe_update(self.stack)
        await asyncio.sleep(round(self.stack.animate_opacity.duration / 1000, 3))
        
        while not self.states.dead:
            if self.states.disable_movement or self.states.disable_movement:
                self.states.is_moving = False
                await asyncio.sleep(0.1)
                continue
            
            dx, dy = 0, 0
            
            # ? Chase Player (if out of range)
            if not self._is_player_in_range():
                if self.target and not self.target.states.dead:
                    self._debug_msg(f"Chasing {self.target.name}", end=" -> ")
                    if self._get_center_point(self.target) > self._get_center_point(self):
                        dx = self.stats.movement_speed
                    elif self._get_center_point(self.target) < self._get_center_point(self):
                        dx = -self.stats.movement_speed
                    self.is_idling = False
                else: self.is_idling = True
                
            else: # ? Attack Player (if in range)
                if self.target and not self.target.states.dead:
                    self._debug_msg("Attacking player")
                    
                    # Predict player if player is jumping
                    if self.target.stack.bottom > self.stack.bottom:
                        self.states.attack_phase = 1
                        if self._get_center_point(self.target) > self._get_center_point(self):
                            dx = -self.stats.movement_speed
                        elif self._get_center_point(self.target) < self._get_center_point(self):
                            dx = self.stats.movement_speed
                        self._check_movement(dx, dy)
                        
                    self.attack()
                    await asyncio.sleep(1)
                    continue
                else: self.is_idling = True
            
            if self.is_idling:
                if self._rnd_dx == 0:
                    if random.randint(1, 10) > 9:
                        self._rnd_dx = random.randint(-1, 1) * self.stats.movement_speed
                else:
                    if random.randint(1, 10) > 7: self._rnd_dx = 0
                    else: dx += self._rnd_dx
            
            self._check_movement(dx, dy)
            if self.states.is_moving:
                self.states.dealing_damage = False
                self._safe_update(self.stack)
            await asyncio.sleep(0.05)
        
    
    # * === ONE-SHOT ANIMATIONS ===
    async def _attack_anim(self):
        """Handles the enemy's attack animations with combos."""
        prefix = f"attack-{self.states.attack_phase}"
        for i in range(8):
            await asyncio.sleep(0.1)
            if self.states.attack_phase == 1:
                if i == 6: self._modify_self_hitbox(width=80, height=80, r_left=10)
            elif self.states.attack_phase == 2:
                if i == 0: self._modify_self_hitbox(r_left=30)
                elif i == 1: self._modify_self_hitbox(r_left=0)
                elif i == 2: self._modify_self_hitbox(r_left=-5, height=60)
                elif i == 5: self._modify_self_hitbox(r_left=50, height=60)
            if i == 5: self._play_sfx(sfx.enemy.boggart_hya)
            elif i == 6:
                self.states.dealing_damage = True
                self._toggle_atk_hb_border()
            elif i == 7:
                self.states.dealing_damage = False
                self._toggle_atk_hb_border()
            self.sprite.change_src(self._get_spr_path(prefix, i))
        self._modify_self_hitbox(reset=True)
        self.states.is_attacking = False
        self._attack_task = None
        self._toggle_atk_hb_border()
    
    async def _death_anim(self):
        """Handles the enemy's death animation."""
        self._update_health_bar()
        self._play_sfx(sfx.enemy.goblin_scream)
        self._play_sfx(sfx.impacts.flesh_impact_2)
        for i in range(4):
            await asyncio.sleep(0.1)
            self.sprite.change_src(self._get_spr_path("death", i))
        self.states.revivable = True
    
    async def _take_hit_anim(self):
        """Handles the enemy's taking damage animation."""
        for i in range(4):
            await asyncio.sleep(0.1)
            self.sprite.change_src(self._get_spr_path("take-hit", i))
            if i == 1:
                self._update_health_bar()
                self._play_sfx(sfx.enemy.goblin_hurt)
                if self.target.states.attack_phase == 1: self._play_sfx(sfx.impacts.flesh_impact_1)
                elif self.target.states.attack_phase == 2: self._play_sfx(sfx.impacts.axe_hit_flesh)
            if i == 2: self._knockback_self(self.target)
        self.states.taking_damage = False
        self._take_hit_task = None
    
    # * === CLEANUP ===
    def remove_selves(self):
        """Removes `self` from `stage` and `_entity_list`."""
        stage = self._get_parent()
        
        self._debug_msg(f"Attempting to remove self from stage: {len(stage.controls)} -> ", end="")
        if self in stage.controls: stage.controls.remove(self.stack)
        self._debug_msg(len(stage.controls), include_handler=False)
        
        self._debug_msg(f"Attempting to remove self from _entity_list: {len(self._entity_list)} -> ", end="")
        if self._entity_list is not None and self in self._entity_list: self._entity_list.remove(self)
        self._debug_msg(len(self._entity_list), include_handler=False)
    
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
        self._debug_msg(f"{self.name} has died!")
        self._update_health_bar()
        
        # ? Animation handling
        attempt_cancel(self._animation_loop_task)
        self._cancel_temp_tasks()
        await self._death_anim()
        self._toggle_atk_hb_border()
        self.states.revivable = True
        await asyncio.sleep(1) # A bit of delay before despawning
        
        # ? Despawn and cleanup
        self.states.revivable = False
        self.stack.opacity = 0
        self._safe_update(self.stack)
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
        self._debug_msg(f"Attacking! Phase: {self.states.attack_phase}")
        self.states.is_attacking = True
        self.states.dealing_damage = False
        self._attack_task = self.page.run_task(self._attack_anim)
    
    async def take_damage(self, damage_amount: float):
        """Decrease enemy's health with logic. Returns `True` if entity has died."""
        if not await super().take_damage(damage_amount): return False
        
        self.states.is_moving = False
        if self.states.is_attacking and random.randint(1, 2) > 1:
            attempt_cancel(self._attack_task)
            self.states.is_attacking = False
            self.states.dealing_damage = False
            self._toggle_atk_hb_border()
            self._modify_self_hitbox(reset=True)
            self._safe_update(self.stack)
            
        if self.stats.health <= 0:
            self.page.run_task(self.death)
            return True
        else:
            if self._take_hit_task: attempt_cancel(self._take_hit_task)
            self._take_hit_task = self.page.run_task(self._take_hit_anim)
            return False
    
    # * === OTHER HELPERS ===
    def _cancel_temp_tasks(self):
        """Cancels all running temporary tasks."""
        tasks = [
            self._attack_task,
            self._take_hit_task
        ]
        for task in tasks: attempt_cancel(task)
    
    def _cancel_loop_tasks(self):
        """Cancels all running looping tasks."""
        tasks = [
            self._movement_loop_task,
            self._damage_detection_task
        ]
        for task in tasks: attempt_cancel(task)
    
    def _is_player_in_range(self):
        """Checks if the specifically targeted player is in range."""
        if self.target is None: return False
        
        # We assume the target (Player) has a sprite and stack
        p_w = self.target.sprite.width
        
        return is_in_x_range(
            entity1_stack=self.stack,
            entity1_w=self.sprite.width,
            entity2_stack=self.target.stack,
            entity2_w=p_w,
            threshold=self.melee_range
        )
        
    # * === COMPONENT METHODS ===
    def _make_stack(self):
        stack = super()._make_stack()
        rnd_duration = random.randint(1000, 2000)
        stack.animate_opacity = ft.Animation(rnd_duration, ft.AnimationCurve.EASE_IN_OUT)
        stack.opacity = 0
        return stack
