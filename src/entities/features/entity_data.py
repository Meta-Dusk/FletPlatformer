from flet import Number
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict
from typing import Literal

from audio.sfx_data import SFXLibrary

ARMOR_SCALING_CONSTANT = 150

class Factions(Enum):
    HUMAN = "Human"
    NONHUMAN = "Non-Human"

@dataclass
class EntityStates:
    """Entity states or state data."""
    # Movement
    is_moving: bool = False
    is_sprinting: bool = False
    jumped: bool = False
    exhausted: bool = False
    is_dashing: bool = False
    restrict_movement: bool = False
    
    # Attacking
    attack_phase: int = 0
    is_attacking: bool = False
    is_falling: bool = False
    dealing_damage: bool = False    
    
    # Flags/Tags
    revivable: bool = False
    invincible: bool = False
    stun_immune: bool = False
    is_healing: bool = False
    is_reviving: bool = False
    
    # Blocking States
    stunned: bool = False
    disable_movement: bool = False
    dead: bool = False
    taking_damage: bool = False

@dataclass
class EntityStats:
    """Includes health, movement speed, etc."""
    # Health
    health: Number = 20.0
    max_health: Number = 20.0
    health_regen: Number = 0.1
    hp_regen_tick: Number = 0.25
    hp_regen_delay: Number = 5
    healing_delay: Number = 0.5
    
    # Stamina
    stamina: Number = 20.0
    max_stamina: Number = 20.0
    stamina_regen: Number = 0.25
    st_regen_tick: Number = 0.1
    st_regen_delay: Number = 3
    st_usage_tick: Number = 0.05
    
    # Movement
    movement_speed: Number = 3.8
    sprint_mult: Number = 1.5
    jump_distance: Number = 15
    jump_strength: Number = 1
    jump_air_time: Number = 0.1
    jump_st_cost: Number = 2
    dash_distance: Number = 3
    dash_strength: Number = 1
    dash_cooldown: Number = 2
    dash_inv_time: Number = 0.2
    dash_st_cost: Number = 5
    dash_duration: Number = 0.2
    exhaustion_modifier: Number = 0.5
    exhaustion_st_multiplier: Number = 2
    
    # Damage
    attack_damage: Number = 5
    attack_knockback: Number = 2
    attack_frame_delay: Number = 0.1
    crit_chance: Number = 5
    crit_damage: Number = 1.5
    
    # Resistance
    knockback_resistance: Number = 1
    armor: Number = 0
    stun_immune_bonus_armor: Number = 0
    
@dataclass
class DebugLogs:
    movement: bool = False
    dash: bool = False
    attack: bool = False
    damage: bool = False
    health: bool = False
    death: bool = False
    revive: bool = False
    stamina: bool = False
    setup: bool = False
    cleanup: bool = False

@dataclass
class AnimConfig:
    frame_count: int
    frame_duration: float
    loop: bool = True
    start_frame: int = 0

AnimationState = Literal[
    "moving", "falling", "idle", "run", "jump", "fall", "attack", "take-hit", "death",
    "revive"
]

@dataclass
class SFXEvent:
    """SFX `Path` and volume."""
    sfx: SFXLibrary
    volume: float

class SFXRegistry:
    """Play SFX at specific frames during specific states."""
    def __init__(self) -> None:
        """Internal storage: (`state`, `frame`) -> `SFXEvent`"""
        self._data: dict[tuple[AnimationState, int], list[SFXEvent]] = defaultdict(list)
        
    def add(self, state: AnimationState, sfx: SFXLibrary, volume: float = 1.0, *, frame: int):
        """Registers an SFX event. Refer to the type hints for `state`."""
        self._data[(state, frame)].append(SFXEvent(sfx, volume))
        
    def get(self, state: AnimationState, frame: int) -> list[SFXEvent]:
        """Returns the associated `SFXEvent`."""
        return self._data.get((state, frame), [])