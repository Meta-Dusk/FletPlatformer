import flet as ft
import math, asyncio
from typing import Literal

from entities.entity import Entity
from entities.projectile import Projectile, ProjectileStats
from utilities.collisions import check_collision
from utilities.components import try_update
from audio.audio_manager import AudioManager
from audio.sfx_data import SFXLibrary

class ProjectileManager:
    def __init__(
        self,
        page: ft.Page,
        audio_manager: AudioManager,
        entity_list: list[Entity] = None,
        ground_level: int = 0,
        *,
        debug: bool = False
    ) -> None:
        self.page = page
        self.audio_manager = audio_manager
        self.entity_list = entity_list
        self.active_projectiles: list[Projectile] = []
        self.projectile_layer = ft.Stack(expand=True, alignment=ft.Alignment.CENTER)
        self.debug = debug
        
        # Physics Configuration
        self.ppm = 50.0       # Pixels Per Meter (Must match PhysicsManager)
        self.ground_level = ground_level
        
    def spawn_projectile(
        self, start_x: float, start_y: float, direction: Literal[-1, 1],
        owner: Entity, stats: ProjectileStats, src: str,
        sfx_upon_spawn: tuple[SFXLibrary, float] = None
    ) -> None:
        # 1. Create
        proj = Projectile(
            start_x, start_y, direction, owner, stats, src,
            self.audio_manager, sfx_upon_spawn=sfx_upon_spawn
        )
        
        # 2. Add to Logic & Visuals
        self.active_projectiles.append(proj)
        self.projectile_layer.controls.append(proj)
        
    def update(self, dt: float):
        to_remove = []
        has_updates = False
        
        if self.active_projectiles:
            has_updates = True
            
            for proj in self.active_projectiles:
                proj.tick_animation(dt)
                stats = proj.stats
                
                # --- A. EXPLOSION LOGIC (The "Grenade" Phase) ---
                if proj.is_exploding:
                    # 1. Check for Damage Frame
                    if (
                        not proj.has_dealt_damage and
                        stats.damage_frame > -1 and
                        proj.current_frame >= stats.damage_frame
                    ):
                        self._apply_area_damage(proj)
                        proj.has_dealt_damage = True
                    
                    if proj.has_dealt_damage:
                        # 2. Check for cleanup
                        if proj.is_dead:
                            to_remove.append(proj)
                        continue # Skip physics for exploding objects
                
                # --- B. PHYSICS ---
                if stats.gravity != 0:
                    proj.dy -= stats.gravity * dt
                
                move_x = proj.dx * self.ppm * dt
                move_y = proj.dy * self.ppm * dt
                
                proj.left += move_x
                proj.bottom += move_y
                
                # --- C. MAP COLLISIONS ---
                if stats.collides_with_map:
                    if proj.bottom < self.ground_level:
                        proj.bottom = self.ground_level
                        
                        # Decide: Bounce or Stick?
                        if stats.bounciness > 0 and abs(proj.dy) > 1.0:
                            proj.dy = -proj.dy * stats.bounciness
                            # Friction on bounce
                            proj.dx *= 0.8 
                        else:
                            proj.dy = 0
                            # Ground Friction
                            if stats.friction > 0 and proj.dx != 0:
                                friction_loss = stats.friction * dt
                                if abs(proj.dx) <= friction_loss:
                                    proj.dx = 0
                                else:
                                    proj.dx -= math.copysign(friction_loss, proj.dx)

                # --- D. BOUNDS & LIFESPAN ---
                is_off_screen = (
                    proj.left < -200 or 
                    proj.left > self.page.width + 200 or 
                    proj.bottom < -200
                )
                
                if is_off_screen and not stats.collides_with_map:
                    to_remove.append(proj)
                    continue

                proj.age += dt
                if proj.age >= stats.lifespan:
                    # [NEW] Timeout Logic: Explode or Delete?
                    if stats.explode_anim:
                        proj.explode()
                    else:
                        to_remove.append(proj)
                    continue
                
                if proj.is_dead:
                    to_remove.append(proj)
                    continue
                
                # --- E. ENTITY COLLISIONS (Impact) ---
                # This only handles direct hits (arrows/bullets), not explosions.
                hit_entity = self._check_entity_impact(proj)
                if hit_entity:
                    # If it's a grenade, hitting an enemy stops it and starts the timer/boom
                    # If it's an arrow (impact_damage=True), it hurts immediately
                    if stats.impact_damage:
                        hit_entity.take_damage(stats.damage)
                        # Knockback
                        k_dir = 1 if proj.dx > 0 else -1
                        hit_entity.velocity.dx += k_dir * proj.stats.impact_knockback
                        to_remove.append(proj)
                    
                    elif stats.explode_anim:
                         # Grenade logic: Hit body -> Stop -> Boom
                         proj.explode()
                
        # --- CLEANUP ---
        if to_remove:
            has_updates = True
            for dead_proj in to_remove:
                if dead_proj in self.active_projectiles:
                    self.active_projectiles.remove(dead_proj)
                if dead_proj in self.projectile_layer.controls:
                    self.projectile_layer.controls.remove(dead_proj)
            
        if has_updates:
            try_update(self.projectile_layer)

    def _get_hitbox(self, entity: Entity) -> tuple[float, float, float, float]:
        """
        Helper: Gets precise hitbox if available, else sprite bounds.
        Returns global (left, bottom, width, height).
        """
        # We use the method explicitly defined in your Entity class
        # which already handles the logic you requested:
        return entity._get_self_global_rect()

    def _check_entity_impact(self, proj: Projectile) -> Entity | None:
        """Checks for direct physical collision between projectile body and entities."""
        if not self.entity_list: return None
        
        p_rect = proj.get_rect()
        
        for entity in self.entity_list:
            if self._should_skip_target(proj, entity): continue
            
            e_rect = self._get_hitbox(entity)
            if check_collision(*p_rect, *e_rect):
                return entity
        return None

    def _apply_area_damage(self, proj: Projectile):
        """
        [NEW] The 'Explosion' detection system.
        Uses a separate check when the explosion animation hits the specific frame.
        """
        if not self.entity_list: return
        
        # Determine Blast Radius
        # Center of the projectile
        center_x = proj.left + (proj.stats.width / 2)
        center_y = proj.bottom + (proj.stats.height / 2)
        
        # Use custom AoE radius or fallback to projectile width * scale
        radius = proj.stats.aoe_radius if proj.stats.aoe_radius > 0 else proj.stats.width * 1.5
        
        # Visualize (Debug)
        if self.debug:
            self._visualize_explosion(center_x, center_y, radius, (proj.stats.height / 2) - 20)
        
        # Create Explosion Rect (Centered)
        exp_rect = (
            center_x - radius, # Left
            center_y - radius, # Bottom
            radius * 2,        # Width
            radius * 2         # Height
        )
        
        for entity in self.entity_list:
            if self._should_skip_target(proj, entity): continue
            
            e_rect = self._get_hitbox(entity)
            
            if check_collision(*exp_rect, *e_rect):
                entity.take_damage(proj.stats.damage)
                
                # Explosion Knockback (Away from center)
                e_center = e_rect[0] + (e_rect[2] / 2)
                dir = 1 if e_center > center_x else -1
                entity.velocity.dx += dir * proj.stats.explosion_knockback
                entity.velocity.dy += proj.stats.explosion_knockback
                
    def _should_skip_target(self, proj: Projectile, entity: Entity) -> bool:
        """Common filter for Friendly Fire and Dead entities."""
        if (
            entity == proj.owner
            or entity.states.dead
            or entity.faction == proj.owner.faction
            or not proj.stats.friendly_fire
        ): return True
        return False
    
    def _visualize_explosion(
        self, center_x: float, center_y: float, radius: float,
        y_offset: ft.Number = 0,
    ) -> None:
        """Spawns a temporary visual indicator for the explosion radius."""
        diameter = radius * 2
        
        # Create a circle representing the blast zone
        indicator = ft.Container(
            left=center_x - radius,
            bottom=center_y - radius - y_offset,
            width=diameter,
            height=diameter,
            border=ft.Border.all(1, ft.Colors.RED), # Clear Red Border
            bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.RED), # Slight tint
            border_radius=radius,
            shape=ft.BoxShape.CIRCLE,
        )
        
        self.projectile_layer.controls.append(indicator)
        # Force an update so it appears immediately
        try_update(self.projectile_layer) 
        
        # Schedule cleanup task (fades out or just removes)
        async def _cleanup():
            await asyncio.sleep(0.3) # Show for 0.3 seconds
            if indicator in self.projectile_layer.controls:
                self.projectile_layer.controls.remove(indicator)
                try_update(self.projectile_layer)
        
        # Use the page reference to run the async task
        self.page.run_task(_cleanup)