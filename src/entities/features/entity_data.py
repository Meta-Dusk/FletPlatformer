from dataclasses import dataclass
from enum import Enum


class Factions(Enum):
    HUMAN = "Human"
    NONHUMAN = "Non-Human"

@dataclass
class EntityStates:
    """Entity states or state data."""
    is_moving: bool = False
    sprint: bool = False
    jumped: bool = False
    attack_phase: int = 0
    is_attacking: bool = False
    is_falling: bool = False
    dead: bool = False
    taking_damage: bool = False
    disable_movement: bool = False
    revivable: bool = False
    dealing_damage: bool = False
    stunned: bool = False
    invincible: bool = False
    stun_immune: bool = False

@dataclass
class EntityStats:
    """Includes health, movement speed, etc."""
    health: float = 20.0
    max_health: float = 20.0
    movement_speed: int = 10
    attack_damage: float = 5.0
    attack_speed: float = 2.0
    jump_distance: int = 100
    jump_strength: float = 1.5
    jump_air_time: float = 0.1
    knockback_resistance: float = 1.0
    attack_knockback: int = 20