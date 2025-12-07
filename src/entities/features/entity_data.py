from dataclasses import dataclass
from enum import Enum

ARMOR_SCALING_CONSTANT = 150

class Factions(Enum):
    HUMAN = "Human"
    NONHUMAN = "Non-Human"

@dataclass
class EntityStates:
    """Entity states or state data."""
    # Movement
    is_moving: bool = False
    sprint: bool = False
    jumped: bool = False
    
    # Attacking
    attack_phase: int = 0
    is_attacking: bool = False
    is_falling: bool = False
    dealing_damage: bool = False    
    
    # Flags/Tags
    revivable: bool = False
    invincible: bool = False
    stun_immune: bool = False
    
    # Blocking States
    stunned: bool = False
    disable_movement: bool = False
    dead: bool = False
    taking_damage: bool = False

@dataclass
class EntityStats:
    """Includes health, movement speed, etc."""
    # Health
    health: float = 20.0
    max_health: float = 20.0
    
    # Movement
    movement_speed: int = 10
    jump_distance: int = 100
    jump_strength: float = 1.5
    jump_air_time: float = 0.1
    dash_distance: int = 100
    dash_strength: float = 1.0
    dash_cooldown: float = 1.0
    dash_inv_perc: float = 0.3
    
    # Damage
    attack_damage: float = 5.0
    attack_speed: float = 2.0
    attack_knockback: int = 20
    
    # Resistance
    knockback_resistance: float = 1.0
    armor: int = 0