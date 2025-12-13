import flet as ft

from utilities.components import try_update
from entities.entity import Entity

class PhysicsManager:
    """Handles all the physics-based motion updates."""
    def __init__(self, page: ft.Page, entity_list: list[Entity]) -> None:
        self.page = page
        self.entity_list = entity_list
        
        # Scaling Constants
        self.ppm = 50.0  # 1 physics unit = n pixels
        
        # Physics Constants
        self.gravity = 9.8 * 3
        self.friction = 5.0
        
    def update(self, dt: float) -> None:
        """Global loop for all physics-based movement."""
        entities_to_update = []
        
        for entity in self.entity_list:
            if not entity or entity.states.disable_movement: continue
            
            # --- A. APPLY GRAVITY ---
            # If above ground, pull down
            if entity.stack.bottom > entity.ground_level:
                entity.velocity.dy -= self.gravity * dt
                entity.on_ground = False
            else:
                entity.on_ground = True
                entity.velocity.dy = max(0, entity.velocity.dy) # Stop falling
                
            # --- B. APPLY VELOCITY ---
            # Velocity (Units/sec) * PPM (Pixels/Unit) * dt (Seconds) = Pixels moved
            
            if entity.velocity.dx != 0:
                entity.stack.left += entity.velocity.dx * self.ppm * dt
            
            if entity.velocity.dy != 0:
                entity.stack.bottom += entity.velocity.dy * self.ppm * dt
            
            # --- C. BOUNDARY CLAMP ---
            # 1. Check Left Wall
            if entity.states.restrict_movement and entity.stack.left < 0:
                entity.stack.left = 0
                entity.velocity.dx = 0 # Stop momentum
                
            # 2. Check Right Wall
            max_x = self.page.width - entity.stack.width
            
            if entity.states.restrict_movement and entity.stack.left > max_x:
                entity.stack.left = max_x
                entity.velocity.dx = 0
            
            # --- D. FLOOR CLAMP ---
            # Hard floor collision
            if entity.stack.bottom < entity.ground_level:
                entity.stack.bottom = entity.ground_level
                entity.velocity.dy = 0
                entity.on_ground = True
                
            # Collect for batch update
            entities_to_update.append(entity.stack)
            
        # 3. BATCH UPDATE
        # Updating specific controls is faster than page.update()
        if entities_to_update: try_update(*entities_to_update)