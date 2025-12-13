import asyncio, random
import flet as ft
from dataclasses import dataclass
from enum import Enum

from entities.entity import Entity
from entities.features.entity_data import EntityStates, EntityStats, Factions, AnimConfig

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

# TODO: Implement more enemy types
class EnemyType(Enum):
    """Available enemy types."""
    FLYING_EYE = EnemyData("Flying Eye") # ! Not yet implemented
    GOBLIN = EnemyData("Gobby", melee_range=120)
    MUSHROOM = EnemyData("Mushy")        # ! Not yet implemented
    SKELETON = EnemyData("Skelly")       # ! Not yet implemented

def get_inversely_scaling_stats(
    rnd_hp_range: tuple[int, int], min_mv_speed: int
) -> tuple[int, int]:
    """
    Calculates an inversely scaling pair of values for
    the HP and movement speed. The higher the HP,
    the lower the movement speed.
    
    Returns:
        tuple: (`rnd_health`, `rnd_mv_speed`)
    """
    rnd_health = random.randint(*rnd_hp_range)
    _, max_hp = rnd_hp_range
    k = max_hp * min_mv_speed
    rnd_mv_speed = round(k / rnd_health)
    return rnd_health, rnd_mv_speed

class Enemy(Entity):
    """Handles an enemy's actions and states."""
    def __init__(
        self,
        type: EnemyType,
        page: ft.Page,
        audio_manager: AudioManager,
        target: Entity = None,
        name: str = None,
        entity_list: list[Entity] = None,
        *,
        debug: bool = False,
        stats: EntityStats = None,
        simple_revive: bool = True
    ) -> None:
        """The main setup for all enemy-type entities."""
        
        # ? Entity inherited class setup
        self._enemy_name = type.name.lower()
        _sprite = Sprite(
            src=f"images/enemies/{self._enemy_name}/idle_0.png",
            width=type.value.width, height=type.value.height
        )
        self.name = type.value.name if name is None else name
        self._init_stats = stats
        
        super().__init__(
            sprite=_sprite, name=self.name, page=page,
            audio_manager=audio_manager, faction=Factions.NONHUMAN,
            entity_list=entity_list, debug=debug, stats=self._init_stats,
            simple_revive=simple_revive
        )
        
        # ? Internal class setup
        self.type = type
        self.target = target
        self._handler_str = self.name
        self.is_idling: bool = False
        self.melee_range: int = type.value.melee_range
        
        self.animations: dict[str, AnimConfig] = {
            "idle": AnimConfig(frame_count=4, frame_duration=0.1),
            "run": AnimConfig(frame_count=6, frame_duration=0.1),
        }
    
    def tick_animation(self, dt: float) -> bool:
        """
        Standard Enemy Animation Logic.
        Can be overridden by subclasses for specific states (Attack/Death).
        """
        new_state = "idle"
        
        if self.states.dead:
            new_state = "death"
        elif self.states.taking_damage:
            new_state = "take-hit"
        elif self.states.is_attacking:
            new_state = "attack"
        elif self.states.is_moving:
            new_state = "run"
            
        # Handle State Change
        if new_state != self.current_anim_state:
            self.current_anim_state = new_state
            self.current_frame = 0
            self.anim_timer = 0.0
            self._update_sprite_src()
            return True

        # Advance Timer
        config = self.animations.get(self.current_anim_state)
        if not config: return False
        
        self.anim_timer += dt
        if self.anim_timer >= config.frame_duration:
            self.anim_timer = 0
            self.current_frame += 1
            
            if self.current_frame >= config.frame_count:
                if config.loop:
                    self.current_frame = 0
                else:
                    self.current_frame = config.frame_count - 1
            
            self._update_sprite_src()
            return True
        return False
    
    # * === CLEANUP ===
    def remove_selves(self) -> None:
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
    def __call__(self, *, start_loops: bool = True, center_spawn: bool = True) -> ft.Stack:
        """
        Returns the `Stack` control, and starts the movement and
        animation loops. Set `center_spawn` to make the enemy spawn
        random across the x-axis.
        """
        if not center_spawn:
            width = self.sprite.width
            new_left = random.randint(width, int(self.page.width)) - width
            self.stack.left = new_left
        if start_loops: self._start_loops()
        return super().__call__()
    
    async def death(self) -> None:
        """Cancels all running tasks, and plays the death animation."""
        if not super().death(): return
        CLEANUP_DELAY: float = 2.0
        
        self._reset_states(EntityStates(dead=True))
        self._update_health_bar()
        self._apply_tint(ft.Colors.RED)
        self._cancel_loop_tasks()
        self._toggle_atk_hb_border()
        
        await asyncio.sleep(CLEANUP_DELAY)
        self.stack.opacity = 0
        try_update(self.stack)
        await await_for_dur(self.stack.animate_opacity)
        self._cleanup_ready = True
        self.states.revivable = True
        
    def attack(self) -> None:
        """
        Enemy attack. Melee combo cycles: 1 -> 2 -> 1.
        Ranged attack based on distance to player.
        """
        if not super().attack(): return
        # self._debug_msg(f"Attacking! Phase: {self.states.attack_phase}", debug_handler=self._debug_logs.attack)
        self.states.is_attacking = True
        self.states.dealing_damage = False
    
    def take_damage(self, damage_amount: float, is_crit: bool = False) -> bool:
        """Decrease enemy's health with logic. Returns `True` if entity has died."""
        if not super().take_damage(damage_amount, is_crit): return False
        self.states.is_moving = False
        self.velocity.dx = 0
        
        # Interruption Logic
        if self.states.is_attacking and not self.states.stun_immune:
            self.states.is_attacking = False
            self.states.dealing_damage = False
            self._toggle_atk_hb_border()
            self._modify_self_hitbox(reset=True)
                
        self._apply_tint(ft.Colors.RED)
        if self.stats.health <= 0:
            self.page.run_task(self.death)
            return True
        return False
    
    async def revive(self) -> None:
        """Revives the enemy."""
        if not super().revive(): return
        self.stack.opacity = 1
        try_update(self.stack)
        await await_for_dur(self.stack.animate_opacity)
    
    # * === OTHER HELPERS ===
    def _start_loops(self) -> None:
        """Starts the looping tasks."""
        self._start_movement_loop()
    
    def _is_target_in_range(self, threshold: float = None) -> bool:
        """Checks if the specifically targeted `Entity` is in range."""
        if self.target is None: return False
        return is_in_x_range(
            entity1_stack=self.stack,
            entity1_w=self.sprite.width,
            entity2_stack=self.target.stack,
            entity2_w=self.target.sprite.width,
            threshold=self.melee_range if threshold is None else threshold
        )
        
    # * === COMPONENT METHODS ===
    def _make_stack(self) -> ft.Stack:
        stack = super()._make_stack()
        rnd_duration = random.randint(1000, 2000)
        stack.animate_opacity = ft.Animation(rnd_duration, ft.AnimationCurve.EASE_IN_OUT)
        stack.opacity = 0
        return stack
