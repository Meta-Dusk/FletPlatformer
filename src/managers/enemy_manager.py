from entities.enemy import EnemyType
from entities.enemy import Enemy
from entities.goblin import Goblin

class EnemyManager:
    """
    Central brain for enemy squad tactics.
    Manages roles (Melee/Ranged) to prevent overcrowding the player.
    """
    def __init__(self):
        # We can store different lists for different factions if needed
        self.active_goblins: list[Goblin] = []
        
        # Tactics Config
        self.goblin_melee_slots: int = 1  # Only 1 goblin can rush the player at a time
        
    def register(self, enemy: Enemy) -> None:
        """Adds an enemy to the tactical tracking list."""
        if enemy.type == EnemyType.GOBLIN and enemy not in self.active_goblins:
            self.active_goblins.append(enemy)
            
    def unregister(self, enemy: Enemy) -> None:
        """Removes an enemy from tracking (e.g., on death)."""
        if enemy in self.active_goblins:
            self.active_goblins.remove(enemy)
            
    def request_melee_role(self, requester: Goblin) -> bool:
        """
        Determines if the requesting goblin is allowed to melee.
        Priority is given to the goblin CLOSEST to the player.
        """
        # Filter only living goblins
        living = [g for g in self.active_goblins if not g.states.dead]
        if not living: return True
        
        # Sort by distance to their target (Player)
        living.sort(key=lambda g: abs(g.target._get_center_point() - g._get_center_point()) if g.target else float('inf'))
        
        # Check Rank
        try:
            rank = living.index(requester)
            return rank < self.goblin_melee_slots
        except ValueError:
            return False