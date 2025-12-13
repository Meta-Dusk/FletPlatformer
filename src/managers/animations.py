import flet as ft
from typing import Protocol

from utilities.components import try_update
from entities.entity import Entity

class Animatable(Protocol):
    """Protocol to ensure entities have the required methods."""
    def tick_animation(self, dt: float) -> bool: ...
    
    @property
    def sprite(self) -> ft.Image: ...
    
    @property
    def states(self): ...

class AnimationManager:
    def __init__(self, entity_list: list[Entity]):
        self.entity_list = entity_list

    def update(self, dt: float):
        """
        Updates the sprite frames for all active entities.
        """
        to_update = []
        
        # Combine Player + Entities into one loop
        # (Filtering out None or dead entities)
        for entity in self.entity_list:
            # Skip if entity is dead or missing
            if not entity or entity.stack.opacity == 0:
                continue
            
            # 1. Tick the Animation
            # The entity calculates "Did my frame change?"
            if hasattr(entity, "tick_animation"):
                did_change = entity.tick_animation(dt)
                
                # 2. Queue for Render
                if did_change:
                    to_update.append(entity.sprite)
        
        # 3. Batch Update Visuals
        if to_update: try_update(*to_update)