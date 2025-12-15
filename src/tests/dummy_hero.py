import random

from entities.entity import Entity

class DummyHero(Entity):
    """A minimal `Entity` subclass for testing that supports `tick_logic`."""
    def __init__(self, sprite, name, page, audio, faction, entity_list):
        super().__init__(sprite, name, page, audio, faction, entity_list)
        self.should_move = False
        self.move_speed = 3.0 # Meters per second
        self.show_hud = False
        
    def tick_logic(self, dt: float) -> None:
        """Handle movement if enabled."""
        if self.states.dead:
            self.velocity.dx = 0
            return
            
        if self.should_move:
            direction = random.choice([-1, 1])
            if self.velocity.dx == 0: self.velocity.dx = self.move_speed * direction
            
            if self.stack.left + self.stack.width >= self.page.width:
                self.velocity.dx = -self.move_speed
                
            elif self.stack.left <= 0: self.velocity.dx = self.move_speed
            
            self.states.is_moving = True
            self._flip_sprite_x(self.velocity.dx)
        else:
            self.velocity.dx = 0
            self.states.is_moving = False