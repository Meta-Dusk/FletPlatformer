from typing import Any

from entities.entity import Entity
from entities.goblin import Goblin
from entities.player import Player
from audio.audio_manager import global_audio_manager
from utilities.keyboard_manager import held_keys

class GameManagerMimic:
    """Temporary class for mimicking the `GameManager`."""
    def __init__(
        self, show_borders: bool,
        entity_list: list[Entity],
        ground_level: int
    ) -> None:
        """Optional init. You don't need to call this inside the `GameManager`."""
        self.show_borders = show_borders
        self.entity_list = entity_list
        self.ground_level = ground_level

# * === MIXINS ===
class GameManagerMixin:
    """Mixin to bridge GameManager data into Entities."""
    def _configure_from_manager(self: Entity, game_manager: GameManagerMimic) -> None:
        """Run this **BEFORE** `super().__init__()` to setup attributes."""
        self.game_manager = game_manager
        self._atk_hb_show = self.game_manager.show_borders
        self._entity_list = self.game_manager.entity_list
        self.ground_level = self.game_manager.ground_level
    
    @property
    def ground_level(self) -> int: return self.game_manager.ground_level
    
    def _get_base_kwargs(self, debug: bool) -> dict[str, Any]:
        """
        Helper for common init arguments. Currently returns the following:
        \n`page`, `audio_manager`, `entity_list`, `debug`.
        """
        return {
            "page": self.game_manager.page,
            "audio_manager": global_audio_manager,
            "entity_list": self.game_manager.entity_list,
            "debug": debug
        }
        
    def _spawn_into_scene(self: Entity, **call_kwargs) -> None:
        """
        Run this **AFTER** `super().__init__()` to add to the game world.
        
        Args:
            **call_kwargs: Arguments passed to `self.__call__()` (i.e., `center_spawn=True`)
        """
        if not isinstance(self, Entity):
            self._debug_msg("Class instance is not an Entity!")
            return
        
        # Apply visual settings that required the stack to exist
        _show = self.game_manager.show_borders
        self.toggle_show_border(show_border=_show, show_atk_hb=_show)
        
        # Add to Logic List (if not already there)
        if self not in self.game_manager.entity_list: self.game_manager.entity_list.append(self)
        
        # Add to Visual Stack
        # ? This calls self.__call__(**kwargs), getting the control and starting loops
        self.game_manager.entity_stack.controls.append(self.__call__(**call_kwargs))

# * --- WRAPPED ENTITIES ---
class NewGoblin(Goblin, GameManagerMixin):
    """
    Wrapped `Enemy` class to be used in the `GameMaker` class.
    Automatically spawns into the scene once called.
    """
    def __init__(
        self, game_manager: GameManagerMimic, name: str = None,
        *, center_spawn: bool = True, debug = False
    ) -> None:
        """Automatically gets spawned into the scene post-init."""
        self._configure_from_manager(game_manager)
        super().__init__(
            target=game_manager.player,
            name=name,
            **self._get_base_kwargs(debug)
        )
        self._spawn_into_scene(center_spawn=center_spawn)

class NewPlayer(Player, GameManagerMixin):
    """
    Wrapped `Player` class to be used in the `GameMaker` class.
    Automatically spawns into the scene once called.
    """
    def __init__(self, game_manager: GameManagerMimic, *, debug = False) -> None:
        """Automatically gets spawned into the scene post-init."""
        self._configure_from_manager(game_manager)
        super().__init__(
            held_keys=held_keys,
            verbose_stamina=game_manager.verbose_stamina,
            **self._get_base_kwargs(debug)
        )
        self._spawn_into_scene()