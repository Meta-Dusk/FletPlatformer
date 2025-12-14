import flet as ft
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from entities.features.entity_data import AnimConfig
from utilities.values import pathify
from utilities.components import try_update

if TYPE_CHECKING:
    from entities.entity import Entity

@dataclass
class Velocity:
    dx: ft.Number = 0.0
    dy: ft.Number = 0.0

@dataclass
class ProjectileStats:
    """Important setup for projectiles."""
    velocity: Velocity = field(default_factory=Velocity)
    damage: ft.Number = 5.0
    gravity: ft.Number = 0.0
    lifespan: ft.Number = 3.0
    friendly_fire: bool = False
    
    # Physics toggles
    collides_with_map: bool = False 
    bounciness: ft.Number = 0.0
    friction: ft.Number = 0.0
    stop_on_explode: bool = False
    
    # Explosion / Damage Logic
    impact_damage: bool = True
    damage_frame: int = -1
    aoe_radius: int = 0
    explosion_knockback: float = 5.0
    impact_knockback: float = 2.0
    
    # Sprite
    width: int = 20
    height: int = 20
    offset: ft.Offset = field(default_factory=ft.Offset)
    
    # Animations
    fly_anim: AnimConfig = None
    explode_anim: AnimConfig = None

@dataclass
class PresetProjectileStats:
    """A list of presets for projectile stats."""
    SmallBomb = ProjectileStats(
        velocity=Velocity(dx=6.0, dy=5.0),
        gravity=15.0,
        lifespan=2.0,
        damage=15,
        friendly_fire=True,
        
        # Grenade Physics
        collides_with_map=True,
        bounciness=0.6,
        friction=10.0,
        stop_on_explode=True,
        
        # Logic
        impact_damage=False,
        damage_frame=9,
        aoe_radius=50,
        
        width=100,
        height=100,
        offset=ft.Offset(0, 0.35),
        
        fly_anim=AnimConfig(frame_count=3, frame_duration=0.1, loop=True, start_frame=0),
        explode_anim=AnimConfig(frame_count=16, frame_duration=0.08, loop=False, start_frame=3),
    )

class Projectile:
    def __init__(
        self, start_x: ft.Number, start_y: ft.Number, 
        direction_x: int,
        owner: "Entity",  
        stats: ProjectileStats,
        src: str
    ) -> None:
        self.owner = owner
        self.stats = stats
        self.age: float = 0.0
        self.is_dead: bool = False
        self.is_exploding: bool = False
        self.has_dealt_damage: bool = False
        
        # Physics State
        self.dx = stats.velocity.dx * direction_x
        self.dy = stats.velocity.dy
        
        # --- ANIMATION STATE ---
        self.anim_timer: float = 0.0
        self.current_frame: int = 0
        self.base_src_path = pathify(src)
        
        # 1. DYNAMIC STATE DETECTION
        # Parses "projectile_0.png" -> state="projectile"
        try:
            stem = self.base_src_path.stem
            name_parts = stem.split("_")
            self.state_name = "_".join(name_parts[:-1]) 
        except (ValueError, IndexError):
            self.state_name = "projectile"

        self.current_config = stats.fly_anim
        
        # Visuals
        _scale = 2
        self.content = ft.Image(
            src=src, fit=ft.BoxFit.CONTAIN,
            filter_quality=ft.FilterQuality.NONE,
            gapless_playback=True, scale=_scale,
            offset=stats.offset
        )
        
        self.stack_obj = ft.Container(
            content=self.content,
            left=start_x, bottom=start_y,
            width=stats.width, height=stats.height,
            alignment=ft.Alignment.CENTER,
        )
    
    def tick_animation(self, dt: float) -> bool:
        """Updates frame. Returns True if visual changed."""
        if not self.current_config: return False
        
        self.anim_timer += dt
        if self.anim_timer >= self.current_config.frame_duration:
            self.anim_timer = 0
            self.current_frame += 1
            
            # Check Finish / Loop
            if self.current_frame >= self.current_config.frame_count:
                if self.current_config.loop:
                    self.current_frame = 0
                else:
                    self.current_frame = self.current_config.frame_count - 1
                    if self.is_exploding:
                        self.is_dead = True
            
            self._update_src()
            return True
        return False

    def explode(self):
        """Triggers the explosion state."""
        if self.is_exploding: return
        
        if self.stats.explode_anim:
            self.is_exploding = True
            
            if self.stats.stop_on_explode:
                self.dx = 0
                self.dy = 0
            
            self.current_config = self.stats.explode_anim
            self.current_frame = 0
            self.anim_timer = 0
            self.has_dealt_damage = False
            self._update_src()
        else:
            self.is_dead = True

    def _update_src(self):
        """Calculates 'folder/state_N.png' using start_frame offset."""
        parent = self.base_src_path.parent
        suffix = self.base_src_path.suffix
        
        # [CHANGE] Add the offset to the current frame index
        # If start_frame is 3, and current_frame is 0, we load image_3.png
        effective_frame = self.current_frame + self.current_config.start_frame
        
        new_path = parent / f"{self.state_name}_{effective_frame}{suffix}"
        self.content.src = new_path.as_posix()
        
        try_update(self.content)
    
    def get_rect(self):
        """Returns (left, bottom, width, height) for collision."""
        return (
            self.stack_obj.left, 
            self.stack_obj.bottom, 
            self.stats.width, 
            self.stats.height
        )