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
    velocity: Velocity = field(default_factory=Velocity)
    damage: ft.Number = 5.0
    gravity: ft.Number = 0.0   # Meters/sec^2 (e.g., 9.8)
    lifespan: ft.Number = 3.0  # Seconds
    
    # Physics toggles
    collides_with_map: bool = False 
    bounciness: ft.Number = 0.0     # 0.0 = Thud, 1.0 = Superball
    friction: ft.Number = 0.0       # Horizontal drag on floor
    
    width: int = 20
    height: int = 20
    offset: ft.Offset = field(default_factory=ft.Offset)
    
    explode_anim: AnimConfig = None
    fly_anim: AnimConfig = None

class Projectile:
    def __init__(
        self, start_x: ft.Number, start_y: ft.Number, 
        direction_x: int, # 1 or -1
        owner: "Entity",  
        stats: ProjectileStats,
        src: str
    ) -> None:
        self.owner = owner
        self.stats = stats
        self.age: float = 0.0
        self.is_dead: bool = False
        self.is_exploding: bool = False
        
        # Physics State (Meters/sec)
        self.dx = stats.velocity.dx * direction_x
        self.dy = stats.velocity.dy
        
        # --- ANIMATION STATE ---
        self.anim_timer: float = 0.0
        self.current_frame: int = 0
        self.base_src_path = pathify(src) # "images/bomb/fly_0.png"
        
        # 1. DYNAMIC STATE DETECTION
        # Parse "projectile_0.png" -> state="projectile", frame=0
        try:
            stem = self.base_src_path.stem # "projectile_0"
            name_parts = stem.split("_")   # ["projectile", "0"]
            
            # The last part is the frame number, everything before is the state name
            self.current_frame = int(name_parts[-1])
            self.state_name = "_".join(name_parts[:-1]) # "projectile"
        except (ValueError, IndexError):
            # Fallback if naming convention isn't followed
            self.current_frame = 0
            self.state_name = "projectile"

        # Determine current config
        self.current_config = stats.fly_anim
        
        # Visuals
        _scale = 2
        self.content = ft.Image(
            src=src, fit=ft.BoxFit.CONTAIN,
            filter_quality=ft.FilterQuality.NONE,
            gapless_playback=True, scale=_scale,
            offset=stats.offset
        )
        
        # Container for positioning
        # (Border removed for production look, add back for debug)
        self.stack_obj = ft.Container(
            content=self.content,
            left=start_x, bottom=start_y,
            width=stats.width, height=stats.height,
            alignment=ft.Alignment.CENTER,
            # border=ft.Border.all(1, ft.Colors.RED) # Uncomment for debug
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
                    # One-shot animation finished (Explosion done)
                    self.current_frame = self.current_config.frame_count - 1
                    if self.is_exploding:
                        self.is_dead = True # NOW we remove it
            
            self._update_src()
            return True
        return False

    def explode(self):
        """Triggers the explosion state."""
        if self.is_exploding: return
        
        if self.stats.explode_anim:
            self.is_exploding = True
            self.dx = 0 # Stop moving
            self.dy = 0
            self.state_name = "projectile"
            self.current_config = self.stats.explode_anim
            self.current_frame = 0
            self.anim_timer = 0
            self._update_src()
        else:
            self.is_dead = True # No anim, just delete

    def _update_src(self):
        """Calculates 'folder/state_N.png'."""
        parent = self.base_src_path.parent
        suffix = self.base_src_path.suffix
        
        new_path = parent / f"{self.state_name}_{self.current_frame}{suffix}"
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