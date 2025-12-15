import flet as ft
from typing import Any, Callable, Literal, TYPE_CHECKING

from entities.enemy import EnemyType, Enemy
from entities.goblin import Goblin
from entities.player import PlayerType, Player
from entities.hero_knight import HeroKnight
from entities.projectile import ProjectileStats

from audio.audio_manager import global_audio_manager
from audio.sfx_data import SFXLibrary

from utilities.keyboard_manager import held_keys

if TYPE_CHECKING:
    from entities.entity import Entity

SoundEffect = tuple[SFXLibrary, float]
Direction = Literal[-1, 1]
SpawnProjectileCallableType = Callable[[float, float, Direction, Entity, ProjectileStats, SoundEffect], None]

# * === TEMP CLASSES (MIMICS) ===
class ProjectileManagerMimic:
    """Temporary class for mimicking the `ProjectileManager`."""
    def __init__(
        self, projectile_layer: ft.Stack,
        spawn_projectile: SpawnProjectileCallableType,
    ):
        """**OPTIONAL** init. You don't need to call this inside the `GameManager`."""
        self.projectile_layer = projectile_layer
        self.spawn_projectile = spawn_projectile

class EnemyManagerMimic:
    def __init__(self):
        pass

class GameLoopMimic:
    """Temporary class for mimicking the `GameLoop`."""
    def __init__(
        self, projectile_manager: ProjectileManagerMimic,
        enemy_manager: EnemyManagerMimic
    ):
        """**OPTIONAL** init. You don't need to call this inside the `GameManager`."""
        self.projectile_manager = projectile_manager
        self.enemy_manager = enemy_manager

class GameManagerMimic:
    """Temporary class for mimicking the `GameManager`."""
    def __init__(
        self, show_borders: bool,
        entity_list: list[Entity],
        ground_level: int,
        entity_stack: ft.Stack,
        page: ft.Page,
        player: Player,
        background_stack: ft.Stack,
        foreground_stack: ft.Stack,
        stage: ft.Stack,
        game_loop: GameLoopMimic,
    ) -> None:
        """**OPTIONAL** init. You don't need to call this inside the `GameManager`."""
        self.show_borders = show_borders
        self.entity_list = entity_list
        self.ground_level = ground_level
        self.entity_stack = entity_stack
        self.page = page
        self.player = player
        self.background_stack = background_stack
        self.foreground_stack = foreground_stack
        self.stage = stage
        self.game_loop = game_loop

# * === MIXINS ===
class GameManagerMixin:
    """Mixin to bridge `GameManager` data into entities."""
    def _configure_from_manager(self: Entity, game_manager: GameManagerMimic) -> None:
        """Run this **BEFORE** `super().__init__()` to setup attributes."""
        self._atk_hb_show = game_manager.show_borders
        self._entity_list = game_manager.entity_list
        self.ground_level = game_manager.ground_level
        self.game_manager = game_manager
    
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
            "projectile_manager": self.game_manager.game_loop.projectile_manager,
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
    Wrapped `Goblin` class to be used in the `GameMaker` class.
    Automatically spawns into the scene once called.
    """
    def __init__(
        self, game_manager: GameManagerMimic, name: str = None,
        *, center_spawn: bool = True, debug = False, enemy_manager = None
    ) -> None:
        """Automatically gets spawned into the scene post-init."""
        self._configure_from_manager(game_manager)
        super().__init__(
            target=game_manager.player,
            name=name,
            enemy_manager=enemy_manager,
            **self._get_base_kwargs(debug)
        )
        self._spawn_into_scene(center_spawn=center_spawn)

class NewHeroKnight(HeroKnight, GameManagerMixin):
    """
    Wrapped `HeroKnight` class to be used in the `GameMaker` class.
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

# * --- FACTORY FUNCTIONS ---
def NewPlayer(
    game_manager: GameManagerMimic, type: PlayerType,
    *, debug: bool = False
) -> Player:
    """
    **Factory Function**: Returns a fully initialized `Player` entity
    wrapped with the `GameManagerMixin`.
    
    Args:
        game_manager (GameManager): Use with the `GameManager` class, and not the mimic.
    """
    match type:
        case PlayerType.HERO_KNIGHT:
            return NewHeroKnight(game_manager, debug=debug)
            
        case _:
            raise NotImplementedError(f"Player type {type.name} is not implemented!")

def NewEnemy(
    game_manager: GameManagerMimic, type: EnemyType,
    *, debug: bool = False, center_spawn: bool = True
) -> Enemy:
    """
    **Factory Function**: Returns a fully initialized `Enemy` entity
    wrapped with the `GameManagerMixin`.
    
    Args:
        game_manager (GameManager): Use with the `GameManager` class, and not the mimic.
    """
    match type:
        case EnemyType.GOBLIN:
            return NewGoblin(
                game_manager, debug=debug, center_spawn=center_spawn,
                enemy_manager=game_manager.game_loop.enemy_manager
            )
            
        case _:
            raise NotImplementedError(f"Enemy type {type.name} is not implemented!")