from typing import TYPE_CHECKING
from entities.enemy import EnemyType

if TYPE_CHECKING:
    from entities.enemy import Enemy
    from entities.goblin import Goblin

class EnemyManager:
    """
    Central brain for enemy squad tactics.
    Manages roles (Melee/Ranged) to prevent overcrowding the player.
    """
    def __init__(self):
        # We can store different lists for different factions if needed
        self.active_goblins: list["Goblin"] = []
        
        # Tactics Config
        self.goblin_melee_slots: int = 1  # Only 1 goblin can rush the player at a time

    def register(self, enemy: "Enemy") -> None:
        """Adds an enemy to the tactical tracking list."""
        if hasattr(enemy, "type") and enemy.type == EnemyType.GOBLIN:
            if enemy not in self.active_goblins:
                self.active_goblins.append(enemy)

    def unregister(self, enemy: "Enemy") -> None:
        """Removes an enemy from tracking (e.g., on death)."""
        if enemy in self.active_goblins:
            self.active_goblins.remove(enemy)

    def request_melee_role(self, requester: "Goblin") -> bool:
        """
        Determines if the requesting goblin is allowed to melee.
        Priority is given to the goblin CLOSEST to the player.
        """
        # 1. Filter only living goblins
        living = [g for g in self.active_goblins if not g.states.dead]
        if not living: return True

        # 2. Sort by distance to their target (Player)
        # We use the helper method _get_center_point which exists on the Entity
        living.sort(key=lambda g: abs(g._get_center_point(g.target) - g._get_center_point(g)) if g.target else float('inf'))

        # 3. Check Rank
        try:
            rank = living.index(requester)
            return rank < self.goblin_melee_slots
        except ValueError:
            return False