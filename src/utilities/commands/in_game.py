import random, inspect
import flet as ft
from typing import Literal, Callable

from entities.entity import Entity
from entities.player import Player
from entities.enemy import EnemyType, Enemy
from utilities.commands.parser import ArgType, BoolArg, IntArg, CoordinateArg, FloatArg, ChoiceArg
from utilities.commands.ui import DevConsole
from utilities.components import try_update


class GameCommands:
    def __init__(
        self, player: Player, entity_list: list[Entity], page: ft.Page,
        console: DevConsole, show_borders: bool,
        summon_enemy: Callable[[str, tuple, tuple, int], list[Entity]] = None
    ) -> None:
        """**OPTIONAL** init. You don't need to call this inside the `GameManager`."""
        self.player = player
        self.entity_list = entity_list
        self.page = page
        self.console = console
        self.show_borders = show_borders
        self.summon_enemy = summon_enemy
    
    # * === HELPER: ENTITY RESOLUTION ===
    def get_targets(
        self, identifier: str, count: int = 1, coords: tuple[int, bool] = None
    ) -> list[Entity]:
        """
        Resolves a string identifier into a list of actual Entity objects.
        
        Args:
            identifier (str): "player", "all", "goblin" (_type_), or "Bob" (_name_)
            count (int): Max number of targets to return (default 1, -1 for all)
            coords (tuple): _Optional_ `(x, is_relative)` to sort by proximity.
        """
        identifier = identifier.lower()
        
        # Collect potential candidates
        if identifier == "player":
            return [self.player] if self.player else []
        
        if identifier == "all":
            candidates = self.entity_list.copy()
        else:
            # Check if it matches an EnemyType enum name (e.g. "goblin")
            is_type_search = any(t.name.lower() == identifier for t in EnemyType)
            
            candidates = []
            for e in self.entity_list:
                # Match by Type (e.g. all goblins)
                if is_type_search and isinstance(e, Enemy) and e.type.name.lower() == identifier:
                    candidates.append(e)
                # Match by Exact Name (e.g. specific boss name)
                elif e.name.lower().replace(" ", "_") == identifier:
                    candidates.append(e)
                    
        # Sort by Proximity (if coords provided)
        if coords:
            target_x, is_rel = coords
            if is_rel: target_x += (self.page.width / 2)
            candidates.sort(key=lambda e: abs(((e.stack.left + e.stack.width) / 2 or 0) - target_x))
            
        # Apply Count Limit
        if count > 0: return candidates[:count]
        return candidates

    # * === COMMANDS REGISTRY ===
    def register_commands(self) -> None:
        """Registers commands specifically for the `GameManager`."""
        # Dynamic Arguments
        entity_arg = EntitySelectorArg(self.entity_list)
        coords_arg = CoordinateArg()
        
        # * --- HANDLERS ---
        # Helper to determine count defaults
        def resolve_count(target: str, user_count: int | None) -> int:
            """
            If user didn't specify a count:
            - target="all" -> Count is Infinite (-1)
            - target="goblin" -> Count is 1
            """
            if user_count is not None: 
                return user_count
            return -1 if target.lower() == "all" else 1
        
        def kill_handler(target: str, x: int = None, y: int = None, count: int = None) -> None:
            # Resolve count logic
            final_count = resolve_count(target, count)
            loc = x if x else None
            
            entities = self.get_targets(target, final_count, loc)
            print(f"target list size: {len(entities)}, entities: {[e.name for e in entities]}")
            
            if not entities:
                self.console.log(f"No targets found for '{target}'", ft.Colors.DEEP_PURPLE)
                return
            
            killed_count = 0
            for e in entities:
                if not e.states.dead:
                    if isinstance(e, Player):
                        e.death()
                    else:
                        self.page.run_task(e.death)
                    killed_count += 1
            
            if killed_count > 0:
                msg_count = "entity" if killed_count == 1 else "entities"
                self.console.log(f"Killed {killed_count} {msg_count}.", ft.Colors.DEEP_PURPLE)
            else:
                self.console.log("Targets are already dead.", ft.Colors.GREY)
                
        def damage_handler(target: str, amount: float, x: int = None, y: int = None, count: int = None) -> None:
            final_count = resolve_count(target, count)
            loc = x if x else None
            
            entities = self.get_targets(target, final_count, loc)
            
            if not entities:
                self.console.log("No targets found.", ft.Colors.PURPLE)
                return
            
            hit_count = 0
            for e in entities:
                if not e.states.dead:
                    e.take_damage(amount)
                    hit_count += 1
            
            if hit_count > 0:
                msg_count = "entity" if hit_count == 1 else "entities"
                self.console.log(f"Damaged {hit_count} {msg_count} for {amount}.", ft.Colors.PURPLE)
                
        def revive_handler(target: str, x: int = None, y: int = None, count: int = None) -> None:
            final_count = resolve_count(target, count)
            loc = x if x else None
            
            entities = self.get_targets(target, final_count, loc)
            
            revived_count = 0
            for e in entities:
                if e.states.dead and e.states.revivable:
                    if isinstance(e, Player):
                        e.revive()
                    else:
                        self.page.run_task(e.revive)
                    revived_count += 1
            
            msg_count = "entity" if revived_count == 1 else "entities"
            self.console.log(f"Revived {revived_count} {msg_count}.", ft.Colors.GREEN)
        
        def summon_handler(enemy_type: str, x: tuple = None, y: tuple = None, count: int = 1) -> None:
            if not self.is_game_running:
                raise Exception("Can only summon entities when the game is running!")
            
            # ? Resolve Type
            try:
                # Convert string (i.e.; "goblin") to Enum (EnemyType.GOBLIN)
                e_enum = EnemyType[enemy_type.upper()]
            except KeyError:
                self.console.log(f"Invalid enemy type: {enemy_type}", ft.Colors.RED)
                return
            
            # ? Determine Spawn Logic
            # If X is provided, we spawn centered first, then move them manually.
            # If X is NOT provided, we let summon_enemy handle random/center logic.
            should_center_spawn = True if x is not None else False
            
            # ? Spawn
            new_entities = self.summon_enemy(e_enum, count, center_spawn=should_center_spawn)
            
            # ? Handle Coordinate Positioning
            if x is not None:
                target_x_val, is_rel = x
                
                # Calculate Base X
                final_x = target_x_val
                if is_rel:
                    # Relative to PLAYER if alive, otherwise relative to SCREEN CENTER
                    if self.player:
                        final_x += self.player.stack.left
                    else:
                        final_x += (self.page.width / 2)
                
                # Apply position to all new entities
                for e in new_entities:
                    # Apply a tiny random offset so they don't stack perfectly on top of each other
                    offset = random.randint(-20, 20) if count > 1 else 0
                    
                    e.stack.left = final_x + offset
                    try_update(e.stack)
                    
            msg_count = "entity" if len(new_entities) == 1 else "entities"
            self.console.log(f"Summoned {len(new_entities)} {msg_count} ({e_enum.name}).", ft.Colors.CYAN)
        
        def toggle_hb_show_handler(enabled: Literal["true", "false"]) -> None:
            _enabled = True if enabled == "true" else False
            self.console.log(f"Setting 'show_borders' to: {_enabled}", ft.Colors.BLUE)
            self.show_borders = _enabled
            for entity in self.entity_list:
                entity.toggle_show_border(show_border=_enabled, show_atk_hb=_enabled)
        
        def force_cleanup_handler() -> None:
            entitites_cleaned: int = 0
            self.console.log("Attempting a forced cleanup on 'entity_list'.")
            for entity in self.entity_list:
                if entity._cleanup_ready and isinstance(entity, Enemy):
                    enemy: Enemy = entity
                    enemy.remove_selves()
                    entitites_cleaned += 1
            self.console.log(f"Entities cleaned up: {entitites_cleaned}.", ft.Colors.ORANGE)
        
        def get_data_handler(var: str, data: str, filter: str) -> None:
            # Identify the Data Source
            source_items = []
            is_logic_entity = False # Flag to know if we can check .states
            
            if var == "entity_list":
                source_items = self.entity_list
                is_logic_entity = True
            elif var == "entity_stack":
                source_items = self.entity_stack.controls
                is_logic_entity = False
            
            # Apply Filtering
            filtered_items = []
            
            if filter == "all":
                filtered_items = source_items
            elif not is_logic_entity:
                # We cannot filter UI controls by "alive/dead" because they don't have states
                self.console.log(f"Warning: Cannot filter '{var}' by state. Returning all.", ft.Colors.ORANGE)
                filtered_items = source_items
            else:
                # Filter Logic Entities
                for e in source_items:
                    is_dead = e.states.dead
                    
                    if filter == "is_alive" and not is_dead:
                        filtered_items.append(e)
                    elif filter == "is_dead" and is_dead:
                        filtered_items.append(e)
                        
            # Format the Output
            output_msg = ""
            
            if data == "len":
                output_msg = f"Count: {len(filtered_items)}"
            
            elif data == "repr_list":
                if is_logic_entity:
                    # For entities, show their Names and IDs/Health as provided in the `__repr__`
                    names = [e for e in filtered_items]
                    output_msg = f"Items: {names}"
                else:
                    # For UI controls, just show their types
                    output_msg = f"Controls: {[type(c).__name__ for c in filtered_items]}"
                    
            # Print to Console
            self.console.log(f"[{var}] {filter} -> {output_msg}", ft.Colors.CYAN)
        
        def heal_handler(
            target: str, amount: float, overheal: Literal["true", "false"],
            x: int = None, y: int = None, count: int = None
        ) -> None:
            _overheal = True if overheal == "true" else False
            final_count = resolve_count(target, count)
            loc = x if x else None
            
            entities = self.get_targets(target, final_count, loc)
            
            if not entities:
                self.console.log("No targets found.", ft.Colors.GREEN)
                return
            
            heal_count = 0
            for e in entities:
                if not e.states.dead:
                    self.page.run_task(e.heal, amount, _overheal)
                    heal_count += 1
            
            if heal_count > 0:
                msg_count = "entities" if heal_count > 1 else "entity"
                self.console.log(f"Healed {heal_count} {msg_count} for {amount}.", ft.Colors.GREEN)
        
        # * --- REGISTRATION ---
        # ? KILL
        self.console.register_command(
            "kill <entity>", kill_handler, 
            {"entity": entity_arg},
            help_text="Kills specific entity or type."
        )
        self.console.register_command(
            "kill <entity> <x> <y> <count>", kill_handler,
            {"entity": entity_arg, "x": coords_arg, "y": coords_arg, "count": IntArg()},
            help_text="Kills <count> of the closest entities to <x> <y>."
        )
        
        # ? DAMAGE
        self.console.register_command(
            "damage <entity> <amount>", damage_handler,
            {"entity": entity_arg, "amount": FloatArg()},
            help_text="Damages target entity."
        )
        self.console.register_command(
            "damage <entity> <amount> <x> <y> <count>", damage_handler,
            {"entity": entity_arg, "amount": FloatArg(), "x": coords_arg, "y": coords_arg, "count": IntArg()},
            help_text="Damages <count> of the closest entities."
        )
        
        # ? REVIVE
        self.console.register_command(
            "revive <entity>", revive_handler,
            {"entity": entity_arg},
            help_text="Revives target."
        )
        self.console.register_command(
            "revive <entity> <x> <y> <count>", revive_handler,
            {"entity": entity_arg, "x": coords_arg, "y": coords_arg, "count": IntArg()},
            help_text="Revives closest targets."
        )
        
        # ? SUMMON
        self.console.register_command(
            "summon <enemy_type>", summon_handler,
            {"enemy_type": EnemyTypeArg()},
            help_text="Summons 1 enemy with random positioning."
        )
        
        self.console.register_command(
            "summon <enemy_type> <x> <y> <count>", summon_handler,
            {"enemy_type": EnemyTypeArg(), "x": coords_arg, "y": coords_arg, "count": IntArg()},
            help_text="Summons <count> enemies at specific coordinates."
        )
        
        # ? GET (Debug Data)
        self.console.register_command(
            "get <var> <data> <filter>", get_data_handler,
            {
                "var": ChoiceArg(["entity_list", "entity_stack"]),
                "data": ChoiceArg(["len", "repr_list"]),
                "filter": ChoiceArg(["all", "is_alive", "is_dead"]) 
            },
            help_text="Get debug data. Filter 'all' for total count."
        )
        
        # ? HEAL
        self.console.register_command(
            "heal <entity> <amount> <overheal>", heal_handler,
            {
                "entity": entity_arg, "amount": FloatArg(),
                "overheal": BoolArg()
            },
            help_text="Heals target entity."
        )
        self.console.register_command(
            "damage <entity> <amount> <overheal> <x> <y> <count>", heal_handler,
            {
                "entity": entity_arg,
                "amount": FloatArg(),
                "overheal": BoolArg(),
                "x": coords_arg, "y": coords_arg,
                "count": IntArg()
            },
            help_text="Heals <count> of the closest entities."
        )
        
        # ? Single Argument Commands
        self.console.register_command(
            "show_borders <enabled>", toggle_hb_show_handler,
            {"enabled": BoolArg()},
            help_text="If enabled, shows all the hitboxes that each entity use."
        )
        
        # ? No Arguments Commands
        self.console.register_command("quit", quit, help_text="Quits to the main menu.")
        self.console.register_command(
            "force_cleanup", force_cleanup_handler, help_text="Force cleanups entities that have despawned.")
        
# * === ARGUMENT TYPES ===
class EntitySelectorArg(ArgType):
    """
    Dynamically allows selection of:
    1. The player instance '**player**'
    2. Specific Enemy Types (i.e.; '**goblin**')
    3. Specific Entity Names (i.e.; '**Gobby**')
    """
    def __init__(self, entity_list: list[Entity]) -> None:
        self.entity_list = entity_list

    def get_suggestions(self, current_input: str) -> list[str]:
        # Always available
        options = {"player", "all"}
        
        # Add Enemy Types (i.e.; "goblin")
        options.update(e.name.lower() for e in EnemyType)
        
        # Add Active Entity Names (i.e.; "Gobby")
        # We filter for active entities to avoid suggesting dead/despawned ones
        if self.entity_list:
            options.update(e.name.replace(" ", "_") for e in self.entity_list)
            
        return [opt for opt in options if opt.lower().startswith(current_input.lower())]

    def parse(self, value: str) -> str:
        # We just pass the string through; the logic handler will resolve it to objects.
        return value

class EnemyTypeArg(ArgType):
    """Strictly selects available EnemyTypes (i.e.; 'goblin')."""
    def get_suggestions(self, current_input: str) -> list[str]:
        return [
            e.name.lower() 
            for e in EnemyType 
            if e.name.lower().startswith(current_input.lower())
        ]
        
    def parse(self, value: str) -> str:
        # Validate that the input is actually a valid enum
        if not any(e.name.lower() == value.lower() for e in EnemyType):
            raise ValueError(f"'{value}' is not a valid Entity Type.")
        return value