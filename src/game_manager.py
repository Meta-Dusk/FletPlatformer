import flet as ft
import asyncio, random
from dataclasses import dataclass

from audio.audio_manager import AudioManager, global_audio_manager
from audio.music_data import MusicLibrary
from components.lups_counter import LupsCounter
from components.menus import MainMenu, PauseMenu, SettingsMenu
from utilities.keyboard_manager import held_keys, start as km_start
from utilities.tasks import attempt_cancel
from entities.player import Player
from utilities.components import try_update
from entities.enemy import EnemyType, Enemy
from entities.entity import Entity
from entities.goblin import Goblin
from bg_loops import light_mv_loop, stage_panning_loop
from backgrounds import add_infinite_layer

music = MusicLibrary()

@dataclass
class GameMenuState:
    main_menu: bool = True
    settings_menu: bool = False
    pause_menu: bool = False

class GameManager:
    """Central hub for the game UI and states."""
    def __init__(self, page: ft.Page):
        # State Variables (References)
        self.page: ft.Page = page
        self.player: Player = None
        self.audio_manager: AudioManager = None
        self.background_stack: ft.Stack = None
        self.foreground_stack: ft.Stack = None
        self.stage: ft.Stack = None
        self.entity_list: list[Entity] = []
        self.menu_state = GameMenuState()
        
        # Task Management
        self.running_tasks: list[asyncio.Task] = []
        
        # World Configuration
        self.ground_level: int = 30
        self.kill_count: int = 0
        self.death_count: int = 0
        self.time: float = 7
        self.is_game_running: bool = False
        
        # Scenes
        async def exit(_): await self.page.window.close()
        self.main_menu = MainMenu(
            on_start=self.start_game,
            on_settings=self.open_settings,
            on_quit=exit
        )
        self.pause_menu = PauseMenu(
            on_resume=self.toggle_pause,
            on_settings=self.open_settings,
            on_quit=self.quit_to_menu
        )
        self.game_layer = ft.Container(
            opacity=0, animate_opacity=ft.Animation(1000, ft.AnimationCurve.LINEAR),
            visible=False
        )
        self.settings_menu = None
    
    # * === IMPORTANT METHODS ===
    async def __call__(self):
        """An alternative way to get the main entry point."""
        await self.initialize()
    
    async def initialize(self):
        """The entry point called by Flet."""
        # --- Setup ---
        self.audio_manager = global_audio_manager
        self.audio_manager.initialize()
        self.audio_manager.play_music(music.loops.sketchbook.abstraction_2023_11_29)
        km_start()
        
        # --- Event Handlers ---
        self.page.on_keyboard_event = self._on_keyboard_event
        self.page.window.on_event = self._win_on_event
        
        # Setup UI: Stack all layers
        self.settings_menu = SettingsMenu(self.audio_manager, on_close=self.close_settings)
        self.stage = ft.Stack(
            controls=[
                self.game_layer,
                self.main_menu,
                self.pause_menu,
                self.settings_menu,
            ], expand=True
        )
        
        self.page.add(self.stage)
        await self.page.window.center()
    
    # * === OTHER HELPERS ===
    def _debug_msg(self, msg: str):
        print(f"[GameManager] {msg}")
    
    def _get_dur(self, control: ft.LayoutControl):
        """
        Returns the opacity animation duration in seconds.
        Assumes that the duration set is of type `int`.
        """
        return round(control.animate_opacity.duration / 1000, 3)
    
    async def _await_for_dur(self, control: ft.LayoutControl):
        """
        Awaits the duration of the animation.
        Assumes that the duration set is of type `int`.
        """
        await asyncio.sleep(self._get_dur(control))
    
    # * === UI SETUP ===
    def _setup_game_ui(self):
        """Initializes Player, Stacks, and HUD."""
        # Stacks/Layers
        self.background_stack = ft.Stack(expand=True)
        self.foreground_stack = ft.Stack(expand=True)
        self.entity_stack = ft.Stack(expand=True)
        self.ui_stack = ft.Stack(expand=True)
        
        def inf_layer(stack: ft.Stack, index: int):
            add_infinite_layer(stack=stack, index=index, page=self.page)
        
        for i in range(1, 8): inf_layer(self.background_stack, i)
        inf_layer(self.background_stack, 9)
        inf_layer(self.foreground_stack, 8)
        inf_layer(self.foreground_stack, 10)
        
        # Buttons / HUD
        death_btn = ft.Button("KYS", ft.Icons.PERSON_OFF, on_click=self._player_die)
        damage_btn = ft.Button("Take Damage", ft.Icons.PERSONAL_INJURY, on_click=self._player_damage)
        revive_btn = ft.Button("Revive", ft.Icons.PERSON_OUTLINE, on_click=self._player_revive)
        self.show_border_sw = ft.Switch(
            adaptive=True, label="Show Bounding Boxes",
            value=False, on_change=self._sb_btn_on_change
        )
        spawn_gobby_btn = ft.Button(
            "Spawn Gobby", ft.Icons.PERSON_ADD,
            on_click=lambda _: self.summon_enemy(EnemyType.GOBLIN, 1)
        )
        buttons_row = ft.Row(
            controls=[
                ft.Container(revive_btn, padding=8),
                ft.Container(death_btn, padding=8),
                ft.Container(damage_btn, padding=8),
                ft.Container(self.show_border_sw, padding=8),
                ft.Container(spawn_gobby_btn, padding=8),
            ], alignment=ft.MainAxisAlignment.CENTER, top=0, left=0
        )
        self.lups_counter = LupsCounter(top=10, right=10)
        
        self.ui_stack.controls.extend([buttons_row, self.lups_counter])
        
        # Composition
        self.game_stage = ft.Stack(
            expand=True,
            controls=[
                self.background_stack,
                self.entity_stack,
                self.foreground_stack,
                self.ui_stack,
            ]
        )
        
        form = ft.WindowDragArea(self.game_stage, expand=True, maximizable=False)
        
        # Player
        self.player = NewPlayer(self)
        return form
        
    # * === EVENT HANDLERS ===
    def _sb_btn_on_change(self, e: ft.ControlEvent):
        for entity in self.entity_list:
            entity.toggle_show_border(e.data)
            entity._atk_hb_show = e.data
    
    async def _player_die(self, _): await self.player.death()
    async def _player_revive(self, _): await self.player.revive()
    async def _player_damage(self, _): await self.player.take_damage(5)
    
    async def _on_keyboard_event(self, e: ft.KeyboardEvent):
        if not self.is_game_running: return
        match e.key:
            case " ": self.player.jump()
            case "V": self.player.attack()
            case "Escape": self.toggle_pause(e)
            case "F11": self.page.window.maximized = not self.page.window.maximized
    
    def _win_on_event(self, e: ft.WindowEvent):
        match e.type:
            case ft.WindowEventType.MAXIMIZE | ft.WindowEventType.UNMAXIMIZE:
                self.settings_menu.fullscreen_toggle.update()
    
    # * === MENU EVENTS ===
    async def start_game(self, _):
        """Switch from Menu to Game"""
        self.main_menu.opacity = 0
        try_update(self.main_menu)
        await self._await_for_dur(self.main_menu)
        self.main_menu.visible = False
        self.main_menu.stop_loop()
        
        self.game_layer.opacity = 0
        self.game_layer.visible = True
        try_update(self.game_layer)
        await asyncio.sleep(0.1)
        self.game_layer.opacity = 1
        self.game_layer.content = self._setup_game_ui()
        try_update(self.game_layer)
        await self._await_for_dur(self.game_layer)
        
        self.audio_manager.play_music(music.loops.sketchbook.abstraction_2024_03_20_02)
        self.is_game_running = True
        self.page.update()
        self.start_tasks()
        self._debug_msg("Starting Game!")
    
    async def open_settings(self, _):
        if self.pause_menu.visible:
            self.pause_menu.opacity = 1
            self.pause_menu.visible = False
            self.settings_menu.opacity = 1
            self.settings_menu.visible = True
            self.settings_menu.subtitle.visible = True
            self.page.update()
        
        elif self.main_menu.visible:    
            self.settings_menu.opacity = 0
            self.settings_menu.visible = True
            self.settings_menu.subtitle.visible = False
            try_update(self.settings_menu)
            await asyncio.sleep(0.1)
            self.settings_menu.opacity = 1
            try_update(self.settings_menu)
    
    async def close_settings(self, _):
        if self.is_game_running:
            self.pause_menu.visible = True
            self.settings_menu.visible = False
            self.page.update()
        
        elif self.main_menu.visible:
            self.settings_menu.opacity = 0
            try_update(self.settings_menu)
            await self._await_for_dur(self.settings_menu)
            self.settings_menu.visible = False
    
    def toggle_pause(self, _):
        """Toggle Pause Overlay"""
        if not self.is_game_running \
        or self.settings_menu.visible: return
        
        self.pause_menu.visible = not self.pause_menu.visible
        try_update(self.pause_menu)
        msg = "Game paused!" if self.pause_menu.visible else "Unpausing game!"
        self._debug_msg(msg)
        
    async def quit_to_menu(self, _):
        """Cleanup game and show menu"""
        self.is_game_running = False
        self.cleanup()
        
        self.game_layer.opacity = 0
        self.pause_menu.opacity = 0
        self.settings_menu.opacity = 0
        try_update(self.page)
        await self._await_for_dur(self.game_layer)
        self.game_layer.content = None
        self.game_layer.visible = False
        self.pause_menu.visible = False
        self.settings_menu.visible = False
        self.pause_menu.opacity = 1
        self.settings_menu.opacity = 1
        try_update(self.page)
        
        self.entity_stack.controls.clear()
        self.entity_list.clear()
        self.game_stage.controls.clear()
        self._debug_msg(f"""
Quitting to Main Menu! Clearing Entities...
entity_list: {len(self.entity_list)}
entity_stack: {len(self.entity_stack.controls)}
        """)
        
        self.main_menu.opacity = 0
        self.main_menu.visible = True
        try_update(self.main_menu)
        await asyncio.sleep(0.1)
        self.audio_manager.play_music(music.loops.sketchbook.abstraction_2023_11_29)
        self.main_menu.opacity = 1
        try_update(self.main_menu)
        await self._await_for_dur(self.main_menu)
        self.main_menu.start_loop()
        
        self.page.update()
    
    # * === GAME EVENTS ===
    def summon_enemy(
        self, enemy_type: EnemyType = None,
        spawn_amount: int = None, center_spawn: bool = False
    ):
        """Summons a random enemy."""
        if enemy_type is None:
            self._debug_msg("Provide an enemy type to summon.")
            return
        if spawn_amount is None: spawn_amount = random.randint(1, 5)
        elif spawn_amount == 0: return
        else: spawn_amount = abs(spawn_amount)
        self._debug_msg(f"Initial entity_stack size: {len(self.entity_stack.controls)}")
        for _ in range(spawn_amount):
            match enemy_type:
                case EnemyType.GOBLIN: NewGoblin(game_manager=self, center_spawn=center_spawn)
                case _: raise NotImplementedError("Other enemy types are not yet implemented!")
        self._debug_msg(f"New entity_stack size: {len(self.entity_stack.controls)}")
    
    # * === TASK MANAGEMENT ===
    def start_tasks(self):
        """Starts background loops."""
        async def run_light(): await light_mv_loop(self.background_stack)
        async def run_pan():
            def summon_gobby(): self.summon_enemy(EnemyType.GOBLIN)
            await stage_panning_loop(
                background_stack=self.background_stack,
                foreground_stack=self.foreground_stack,
                page=self.page,
                player=self.player,
                entity_list=self.entity_list,
                stage=self.stage,
                post_callback=summon_gobby
            )
            
        # Store tasks so we can cancel them later
        self.running_tasks.append(self.page.run_task(run_light))
        self.running_tasks.append(self.page.run_task(run_pan))
        
    def cleanup(self):
        """Call this when exiting or changing levels."""
        for task in self.running_tasks: attempt_cancel(task)
        for entity in self.entity_list:
            if isinstance(entity, Enemy):
                entity._cancel_loop_tasks()
                entity._cancel_temp_tasks()
                
class GameManagerMixin:
    """Mixin to bridge GameManager data into Entities."""
    def _configure_from_manager(self: Entity, game_manager: GameManager):
        """Run this **BEFORE** `super().__init__()` to setup attributes."""
        self.game_manager = game_manager
        self._atk_hb_show = self.game_manager.show_border_sw.value
        self._entity_list = self.game_manager.entity_list
    
    @property
    def ground_level(self) -> int: return self.game_manager.ground_level
    
    def _get_base_kwargs(self, debug: bool):
        """
        Helper for common init arguments. Currently returns the following:
        \n`page`, `audio_manager`, `entity_list`, `debug`.
        """
        return {
            "page": self.game_manager.page,
            "audio_manager": self.game_manager.audio_manager,
            "entity_list": self.game_manager.entity_list,
            "debug": debug
        }
        
    def _spawn_into_scene(self: Entity, **call_kwargs):
        """
        Run this **AFTER** `super().__init__()` to add to the game world.
        
        Args:
            **call_kwargs: Arguments passed to `self.__call__()` (i.e., `center_spawn=True`)
        """
        if not isinstance(self, Entity):
            self._debug_msg("Class instance is not an Entity!")
            return
        
        # Apply visual settings that required the stack to exist
        self.toggle_show_border(self.game_manager.show_border_sw.value)
        self._atk_hb_show = self.game_manager.show_border_sw.value
        
        # Add to Logic List (if not already there)
        if self not in self.game_manager.entity_list: self.game_manager.entity_list.append(self)
        
        # Add to Visual Stack
        # ? This calls self.__call__(**kwargs), getting the control and starting loops
        self.game_manager.entity_stack.controls.append(self.__call__(**call_kwargs))
        
class NewGoblin(Goblin, GameManagerMixin):
    """
    Wrapped `Enemy` class to be used in the `GameMaker` class.
    Automatically spawns into the scene once called.
    """
    def __init__(
        self, game_manager: GameManager, name: str = None,
        *, center_spawn: bool = True, debug = False
    ):
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
    def __init__(
        self, game_manager: GameManager, *, debug = False
    ):
        self._configure_from_manager(game_manager)
        super().__init__(
            held_keys=held_keys,
            **self._get_base_kwargs(debug)
        )
        self._spawn_into_scene()