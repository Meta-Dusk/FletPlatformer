import flet as ft

from entities.entity import Entity
from entities.projectile import Projectile, ProjectileStats
from utilities.collisions import check_collision
from utilities.components import try_update

class ProjectileManager:
    def __init__(
        self, page: ft.Page, entity_list: list[Entity] = None,
        ground_level: int = 0
    ) -> None:
        self.page = page
        self.entity_list = entity_list
        self.active_projectiles: list[Projectile] = []
        self.projectile_layer = ft.Stack(expand=True, alignment=ft.Alignment.CENTER)
        
        # Physics Configuration
        self.ppm = 50.0       # Pixels Per Meter (Must match PhysicsManager)
        self.ground_level = ground_level
        
    def spawn_projectile(
        self, start_x: float, start_y: float, direction: int,
        owner: Entity, stats: ProjectileStats, src: str
    ) -> None:
        # 1. Create
        proj = Projectile(start_x, start_y, direction, owner, stats, src)
        
        # 2. Add to Logic & Visuals
        self.active_projectiles.append(proj)
        self.projectile_layer.controls.append(proj.stack_obj)
        
    def update(self, dt: float):
        """Global loop for all projectiles."""
        to_remove = []
        has_updates = False
        
        if self.active_projectiles:
            has_updates = True
            
            for proj in self.active_projectiles:
                proj.tick_animation(dt)
                
                # If exploding, skip physics and collisions
                if proj.is_exploding:
                    if proj.is_dead: # Animation finished
                        to_remove.append(proj)
                    continue
                
                stats = proj.stats
                
                # --- 1. APPLY GRAVITY ---
                if stats.gravity != 0:
                    proj.dy -= stats.gravity * dt
                
                # --- 2. APPLY MOVEMENT (Scaled by PPM) ---
                move_x = proj.dx * self.ppm * dt
                move_y = proj.dy * self.ppm * dt
                
                proj.stack_obj.left += move_x
                proj.stack_obj.bottom += move_y
                
                # --- 3. MAP COLLISIONS ---
                if stats.collides_with_map:
                    # 1. Check Floor Collision FIRST
                    if proj.stack_obj.bottom < self.ground_level:
                        proj.stack_obj.bottom = self.ground_level
                        
                        # 2. NOW decide: Explode or Bounce?
                        if stats.explode_anim:
                            proj.explode() # Triggers animation, freezes physics
                        else:
                            # Standard Bounce / Friction Logic
                            if stats.bounciness > 0 and abs(proj.dy) > 1.0:
                                proj.dy = -proj.dy * stats.bounciness
                            else:
                                proj.dy = 0
                                if stats.friction > 0 and proj.dx != 0:
                                    friction_loss = stats.friction * dt
                                    if abs(proj.dx) <= friction_loss:
                                        proj.dx = 0
                                    else:
                                        proj.dx -= friction_loss if proj.dx > 0 else -friction_loss
                                    
                # --- 4. BOUNDS & LIFESPAN CHECK ---
                # Remove if off-screen (unless it's a map object that should stay)
                is_off_screen = (
                    proj.stack_obj.left < -200 or 
                    proj.stack_obj.left > self.page.width + 200 or 
                    proj.stack_obj.bottom < -200
                )
                
                # If it's a "physical" object (collides_with_map), we let it stay on the floor.
                # If it's a "magic" object (no collision), off-screen means delete.
                if is_off_screen and not stats.collides_with_map:
                    to_remove.append(proj)
                    continue

                # Age Check
                proj.age += dt
                if proj.age >= stats.lifespan:
                    to_remove.append(proj)
                    continue
                
                # TODO: Rework entity collisions to also use hitboxes
                # --- 5. ENTITY COLLISIONS (Implemented) ---
                if not self.entity_list: continue

                p_rect = proj.get_rect()
                hit_something = False
                
                for entity in self.entity_list:
                    # Skip self, dead entities, and same faction (Friendly Fire protection)
                    if (entity == proj.owner or 
                        entity.states.dead or 
                        (hasattr(entity, "faction") and entity.faction == proj.owner.faction)):
                        continue
                    
                    e_rect = entity._get_self_global_rect()
                    
                    if check_collision(*p_rect, *e_rect):
                        # HIT!
                        # TODO: Rework damage to only apply when exploding
                        entity.take_damage(stats.damage)
                        
                        # Apply Knockback
                        knockback_dir = 1 if proj.dx > 0 else -1
                        entity.velocity.dx += knockback_dir * 2.0
                        
                        # --- MODIFIED LOGIC ---
                        if stats.explode_anim:
                            proj.explode() # Freeze physics, start boom
                            # Do NOT append to to_remove yet; 
                            # the 'is_exploding' check at the top of the loop will handle removal later.
                        else:
                            to_remove.append(proj) # No anim, delete instantly
                            
                        hit_something = True
                        # break
                
                if hit_something: continue

        # --- CLEANUP & RENDER ---
        if to_remove:
            has_updates = True
            for dead_proj in to_remove:
                if dead_proj in self.active_projectiles:
                    self.active_projectiles.remove(dead_proj)
                if dead_proj.stack_obj in self.projectile_layer.controls:
                    self.projectile_layer.controls.remove(dead_proj.stack_obj)
            
        if has_updates:
            try_update(self.projectile_layer)