import flet as ft
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from entities.features.entity_data import AnimConfig, SFXRegistry
from audio.audio_manager import AudioManager
from audio.sfx_data import SFXLibrary
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
    sfx_registry: SFXRegistry = field(default_factory=SFXRegistry)
    
    # Physics toggles
    collides_with_map: bool = False 
    bounciness: ft.Number = 0.0
    friction: ft.Number = 0.0
    stop_on_explode: bool = False
    is_parryable: bool = False
    
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

# Registering SFX for projectile presets
sfx = SFXLibrary()

small_bomb_sfx = SFXRegistry()
small_bomb_sfx.add("fly", sfx.explosions.light_spark_sizzle, volume=0.5)
small_bomb_sfx.add("explode", sfx.explosions.small, volume=0.5, frame=9)

banshee_blast_sfx = SFXRegistry()
banshee_blast_sfx.add("explode", sfx.whoosh.swish_blast_2, volume=0.5)

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
        is_parryable=True,
        
        # Logic
        impact_damage=False,
        damage_frame=9,
        aoe_radius=50,
        
        width=100, height=100,
        offset=ft.Offset(0, 0.35),
        
        fly_anim=AnimConfig(frame_count=3, frame_duration=0.1),
        explode_anim=AnimConfig(frame_count=16, frame_duration=0.08, loop=False, start_frame=3),
        sfx_registry=small_bomb_sfx
    )
    BansheeBlast = ProjectileStats(
        velocity=Velocity(dx=10.0, dy=10.0),
        gravity=0,
        lifespan=1.0,
        damage=8,
        
        collides_with_map=True,
        stop_on_explode=True,
        is_parryable=True,
        
        impact_damage=False,
        damage_frame=0,
        aoe_radius=30,
        
        width=48, height=48,
        
        fly_anim=AnimConfig(frame_count=3, frame_duration=0.1),
        explode_anim=AnimConfig(frame_count=8, frame_duration=0.1, loop=False, start_frame=3),
        sfx_registry=banshee_blast_sfx
    )

class Projectile(ft.Container):
    def __init__(
        self, start_x: ft.Number, start_y: ft.Number, 
        direction_x: int,
        owner: "Entity",  
        stats: ProjectileStats,
        src: str,
        audio_manager: AudioManager,
        *,
        sfx_upon_spawn: tuple[SFXLibrary, float] = None
    ) -> None:
        self.owner = owner
        self.stats = stats
        self.age: float = 0.0
        self.is_dead: bool = False
        self.is_exploding: bool = False
        self.has_dealt_damage: bool = False
        self.audio_manager = audio_manager
        self.sfx_upon_spawn = sfx_upon_spawn
        
        # Physics State
        self.dx = stats.velocity.dx * direction_x
        self.dy = stats.velocity.dy
        
        # --- ANIMATION STATE ---
        self.anim_timer: float = 0.0
        self.current_frame: int = 0
        self.base_src_path = pathify(src)
        
        # DYNAMIC STATE DETECTION
        # Parses "projectile_0.png" -> state="projectile"
        try:
            stem = self.base_src_path.stem
            name_parts = stem.split("_")
            self.state_name = "_".join(name_parts[:-1]) 
        except (ValueError, IndexError):
            self.state_name = "projectile"

        self.current_config = stats.fly_anim
        
        # Callables
        self.play_sfx: Callable[[SFXLibrary, float], None] = None
        
        # Visuals
        _scale = 2
        self.sprite = ft.Image(
            src=src, fit=ft.BoxFit.CONTAIN,
            filter_quality=ft.FilterQuality.NONE,
            gapless_playback=True, scale=_scale,
            offset=stats.offset,
            color_blend_mode=ft.BlendMode.SRC_A_TOP
        )
        
        super().__init__(
            content=self.sprite,
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
            
            current_state_key = "explode" if self.is_exploding else "fly"
            events = self.stats.sfx_registry.get(current_state_key, self.current_frame)
            if events and len(events) > 0:
                for event in events:
                    if self.play_sfx:
                        self.play_sfx(event.sfx, event.volume)
            
            self._update_src()
            return True
        return False
    
    def did_mount(self):
        self.play_sfx = self._play_sfx
        self.play_sfx(*self.sfx_upon_spawn)
    
    def _play_sfx(self, sfx: SFXLibrary, volume: float = None) -> None:
        """Play an SFX with directional playback based on projectile position."""
        if not self.audio_manager: return
        
        # Calculate panning based on screen position
        right_vol = (self.left + (self.stats.width / 2)) / self.page.width
        left_vol = 1.0 - right_vol
        
        self.audio_manager.play_sfx(
            sfx_path=sfx,
            left_volume=left_vol,
            right_volume=right_vol,
            base_volume=volume
        )
    
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
            
            events = self.stats.sfx_registry.get("explode", 0)
            if events and len(events) > 0:
                for event in events:
                    if self.play_sfx:
                        self.play_sfx(event.sfx, event.volume)
            
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
            self.left, self.bottom,
            self.stats.width, self.stats.height
        )
    
    def parry(self, new_owner: "Entity") -> bool:
        """
        Reflects the projectile back at the shooter.
        Returns `True` if successful.
        """
        # 1. Validation
        if (
            not self.stats.is_parryable
            or self.is_exploding
            or self.is_dead
        ): 
            return False
        
        # 2. Swap Ownership (Now it hurts the enemy!)
        self.owner = new_owner
        
        # 3. Reverse & Boost Physics
        # Flip X direction and add speed to make it feel powerful
        self.dx *= -1 * new_owner.stats.attack_knockback
        
        # Pop it up slightly in the air if it was falling
        self.dy = abs(self.dy) + new_owner.stats.attack_knockback
        
        # 4. Reset Damage Flags (For grenades/piercing)
        self.has_dealt_damage = False
        
        # 5. Visual Feedback (Optional: Reset tint or flash)
        self.sprite.color = ft.Colors.with_opacity(0.5, ft.Colors.WHITE)
        try_update(self.content)
        
        return True