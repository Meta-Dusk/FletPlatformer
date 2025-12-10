import flet as ft
import asyncio, random
from typing import Any

from audio.audio_manager import global_audio_manager
from audio.music_data import MusicLibrary

from components.menus import MainMenu, PauseMenu, SettingsMenu
from components.displays import StatsDisplay
from components.custom_switches import TextAndToggle
from components.popups import SimpleNotification, SimpleDialog

from utilities.keyboard_manager import held_keys, start as km_start
from utilities.tasks import attempt_cancel
from utilities.components import try_update
from utilities.commands.ui import DevConsole
from utilities.commands.in_game import GameCommands
from utilities.performance_monitor import PerformanceMonitor
from utilities.tutorial_handler import TutorialHandler

from entities.player import Player
from entities.enemy import EnemyType, Enemy
from entities.entity import Entity
from entities.goblin import Goblin

from bg_loops import light_mv_loop, stage_panning_loop
from backgrounds import add_infinite_layer

music = MusicLibrary()
audio_manager = global_audio_manager

class GameManager(GameCommands):
    """Central hub for the game UI and states."""
    def __init__(self, page: ft.Page) -> None:
        # State Variables (References)
        self.page: ft.Page = page
        self.player: Player = None
        
        # UI Layers
        self.background_stack = ft.Stack(expand=True, alignment=ft.Alignment.CENTER)
        self.foreground_stack = ft.Stack(expand=True, alignment=ft.Alignment.CENTER)
        self.entity_stack = ft.Stack(expand=True, alignment=ft.Alignment.CENTER)
        self.ui_stack = ft.Stack(expand=True, alignment=ft.Alignment.CENTER)
        self.stage = ft.Stack(expand=True, alignment=ft.Alignment.CENTER)
        self.game_stage = ft.Stack(expand=True, alignment=ft.Alignment.CENTER)
        self.entity_list: list[Entity] = []
        self.console = DevConsole()
        self.stats_panel: StatsDisplay = None
        self.tutorial_handler = TutorialHandler(self.page, self._on_finish_tutorial)
        
        # Task Management
        self.running_tasks: list[asyncio.Task] = []
        
        # World Configuration
        self.ground_level: int = 30
        self.is_game_running: bool = False
        
        # Properties
        self._show_borders: bool = False
        self._death_count: int = 0
        self._kill_count: int = 0
        
        # Other Settings
        self.verbose_stamina: bool = False
        
        # Scenes
        self.main_menu = None
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
    
    # * === GAME PROPERTIES ===
    @property
    def show_borders(self) -> bool:
        return self._show_borders
    
    @show_borders.setter
    def show_borders(self, enabled: bool) -> None:
        self._show_borders = enabled
    
    @property
    def kill_count(self) -> int:
        """Returns the current kills of the player."""
        return self._kill_count
    
    @kill_count.setter
    def kill_count(self, amount: int) -> None:
        """
        Increases the player's kill count by `amount` and
        updates the associated UI control.
        """
        self._kill_count = amount
        if hasattr(self, "kill_count_text"):
            self.kill_count_text.spans[1].text = self._kill_count
            try_update(self.kill_count_text)
    
    @property
    def death_count(self) -> int:
        """Returns the current deaths of the player."""
        return self._death_count
    
    @death_count.setter
    def death_count(self, amount: int) -> None:
        """
        Increases the player's death count by `amount` and
        updates the associated UI control.
        """
        self._death_count = amount
        if hasattr(self, "death_count_text"):
            self.death_count_text.spans[1].text = self._death_count
            try_update(self.death_count_text)
    
    # * === MENUS ===
    def _make_main_menu(self) -> None:
        """Assembles the Main Menu."""
        async def exit(_): await self.page.window.close()
        self.main_menu = MainMenu(
            on_start=self.start_game,
            on_settings=self.open_settings,
            on_quit=exit
        )
        if not self.main_menu in self.stage.controls:
            self.stage.controls.insert(1, self.main_menu)
        try_update(self.stage)
    
    def _remove_main_menu(self):
        """Removes the Main Menu."""
        self.stage.controls.remove(self.main_menu)
        try_update(self.stage)
    
    # * === IMPORTANT METHODS ===
    async def __call__(self) -> None:
        """An alternative way to get the main entry point."""
        await self.initialize()
    
    async def initialize(self) -> None:
        """The entry point called by Flet."""
        # --- Setup ---
        audio_manager.play_music(music.loops.sketchbook.abstraction_2023_11_29)
        km_start()
        self.register_commands()
        
        # --- Event Handlers ---
        self.page.on_keyboard_event = self._on_keyboard_event
        self.page.window.on_event = self._win_on_event
        
        # Setup UI: Stack all layers
        self._make_main_menu()
        self.settings_menu = SettingsMenu(audio_manager, on_close=self.close_settings)
        self.stage.controls.extend([
            self.game_layer,
            self.pause_menu,
            self.settings_menu,
        ])
        
        # Post Setup for UI
        self.settings_menu.console_switch.switch.on_toggle = self._console_on_toggle
        self.settings_menu.stamina_toggles.switch.on_toggle = self._stamina_verbose_toggle
        self.perf_monitor = PerformanceMonitor()
        perf_toggles = self.settings_menu.perf_toggles
        perf_toggles.monitor_switch.switch.on_toggle = self._perf_monitor_toggle
        perf_toggles.ups_switch.switch.on_toggle = lambda b: self.perf_monitor.toggle_ups(b)
        perf_toggles.lag_switch.switch.on_toggle = lambda b: self.perf_monitor.toggle_latency(b)
        
        self.page.add(self.stage)
        await self.page.window.center()
        self.page.window.maximized = True
    
    # * === OTHER HELPERS ===
    def _debug_msg(self, msg: str) -> None:
        """A very simple debug logger."""
        print(f"[GameManager] {msg}")
    
    async def _await_for_dur(self, control: ft.LayoutControl) -> None:
        """
        Awaits the duration of the animation.
        Assumes that the duration set is of type `int`.
        """
        seconds = round(control.animate_opacity.duration / 1000, 3)
        await asyncio.sleep(seconds)
    
    # * === UI SETUP ===
    def _setup_game_ui(self):
        """Initializes Player, Stacks, and HUD."""
        # Player
        self.player = NewPlayer(self)
        self.player.on_death = self._on_player_death
        self.player.on_kill = self._on_player_kill
        
        # Stacks/Layers
        def inf_layer(stack: ft.Stack, index: int):
            add_infinite_layer(stack=stack, index=index, page=self.page)
        
        for i in range(1, 8): inf_layer(self.background_stack, i)
        inf_layer(self.background_stack, 9)
        inf_layer(self.foreground_stack, 8)
        inf_layer(self.foreground_stack, 10)
        
        # Buttons / HUD
        stats_switch = TextAndToggle(
            label_text="Show Stats", label_size=15, right=200, top=10,
            spacer_width=0, width=50, height=25
        )
        stats_switch.switch.on_toggle = self._toggle_stats_panel
        self.stats_panel = StatsDisplay(self.player.stats)
        self.ui_stack.controls.extend([stats_switch, self.stats_panel])
        if not self.tutorial_handler.finished_tutorial:
            self.ui_stack.controls.insert(0, self.tutorial_handler())
        
        self.kill_count_text = ft.Text(
            spans=[
                ft.TextSpan("Kills: "),
                ft.TextSpan(self.kill_count)
            ], size=20, text_align=ft.TextAlign.START
        )
        self.death_count_text = ft.Text(
            spans=[
                ft.TextSpan("Deaths: "),
                ft.TextSpan(self.death_count)
            ], size=20, text_align=ft.TextAlign.START
        )
        self.stats_view = ft.Column(
            controls=[self.kill_count_text, self.death_count_text],
            spacing=4, left=10, top=10,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        )
        
        # Composition
        self.game_stage.controls.extend([
            self.background_stack,
            self.entity_stack,
            self.foreground_stack,
            self.ui_stack,
        ])
        
        form = ft.WindowDragArea(self.game_stage, expand=True, maximizable=False)
        return form
        
    # * === EVENT HANDLERS ===
    def _toggle_stats_panel(self, enabled: bool):
        """
        Toggles the visibility of the stats panel,
        and updates its contents.
        """
        self.stats_panel.visible = enabled
        self.stats_panel._update_texts()
        try_update(self.stats_panel)
    
    async def _on_keyboard_event(self, e: ft.KeyboardEvent):
        """Handles various 'on-press' keyboard events."""
        # Window and Dev keybinds
        match e.key:
            case "F11": self.page.window.maximized = not self.page.window.maximized
            case "/":
                if not self.console in self.page.overlay: return
                await self.console.toggle()
                self._update_ui_focus()
            case "Escape":
                if self.console.visible:
                    await self.console.toggle()
                    self._update_ui_focus()
                elif self.settings_menu.visible:
                    self.close_settings(e)
                else:
                    self.toggle_pause(e)
        await self.console.handle_keyboard(e)
        
        # Player Keybinds
        if not self.is_game_running or (self.player and self.player.states.disable_movement):
            return
        
        match e.key:
            case " ": self.player.jump()
            case "V": self.player.attack()
        
        self.tutorial_handler._on_keyboard_event(e)
    
    def _on_finish_tutorial(self) -> None:
        """Removes the tutorial controls after finishing the tutorial."""
        self._debug_msg("Finished tutorial!")
        self._start_stage_panning()
        self.ui_stack.controls.remove(self.tutorial_handler.tutorial)
        self.ui_stack.controls.append(self.stats_view)
        tutorial_dlg = SimpleDialog(
            title="Key Binds Tutorial",
            content="You've finished the tutorial! You can now go ahead an go beyond the starting area."
        )
        self.page.overlay.append(tutorial_dlg)
        self.ui_stack.update()
    
    def _win_on_event(self, e: ft.WindowEvent):
        """Updates controls that reflect the window's properties."""
        match e.type:
            case ft.WindowEventType.MAXIMIZE | ft.WindowEventType.UNMAXIMIZE:
                self.settings_menu.fullscreen_toggle.update()
        self.settings_menu.win_on_update(e)
    
    def _stamina_verbose_toggle(self, enabled: bool) -> None:
        """Toggles the player's stamina verbose toggle."""
        if self.player:
            self.player._stamina_bar_stack.verbose = enabled
        self.verbose_stamina = enabled
    
    def _console_on_toggle(self, enabled: bool) -> None:
        """Adds/removes the developer conosle in the page's overlay."""
        if enabled:
            self._debug_msg("Enabling dev console...")
            notif = SimpleNotification("Enabling the Dev Console!", width=250)
            self.page.overlay.extend([self.console, notif])
        else:
            self._debug_msg("Disabling dev console... 1/2")
            if self.console in self.page.overlay:
                self.console.visible = False
                self.page.overlay.remove(self.console)
                notif = SimpleNotification("Disabling the Dev Console!", width=250)
                self.page.overlay.append(notif)
                self._debug_msg("Disabling dev console... 2/2")
        self.page.update()
        self._update_ui_focus()
    
    def _perf_monitor_toggle(self, enabled: bool) -> None:
        """Adds/removes the performance monitor in the page's overlay."""
        if enabled:
            self.page.overlay.insert(1, self.perf_monitor)
            self.page.update()
        else:
            self.page.overlay.remove(self.perf_monitor)
    
    def _on_player_death(self) -> None:
        """Incremets the death counter on player death."""
        self.death_count += 1
        self._debug_msg(f"Death count: {self.death_count}")
    
    def _on_player_kill(self) -> None:
        """Increments the kill counter on player kill."""
        self.kill_count += 1
        self._debug_msg(f"Kill Count: {self.kill_count}")
    
    # * === UI MANAGEMENT ===
    def _update_ui_focus(self):
        """
        Centralized logic to determine which UI layer should be interactive.
        Priority Order (Highest to Lowest):
        1. Dev Console
        2. Settings Menu
        3. Pause Menu
        4. Main Menu
        5. Game HUD (Entity movement / On-screen buttons)
        """
        # 1. Check Console (Top Priority)
        if self.console in self.page.overlay and self.console.visible:
            self._set_interactivity()
            return
        
        # 2. Check Settings (Can be opened from Main Menu OR Pause Menu)
        if self.settings_menu.visible:
            self._set_interactivity(settings=True)
            return
        
        # 3. Check Pause Menu (In-Game Overlay)
        if self.pause_menu.visible:
            self._set_interactivity(pause=True)
            return
        
        # 4. Check Main Menu (Start Screen)
        if self.main_menu in self.stage.controls and self.main_menu.visible:
            self._set_interactivity(main_menu=True)
            return
        
        # 5. Game Layer (Lowest Priority - only active if nothing else is)
        if self.is_game_running and self.game_layer.visible:
            self._set_interactivity(game_hud=True)
            return
        
    def _set_interactivity(
        self,
        settings: bool = False,
        pause: bool = False,
        main_menu: bool = False,
        game_hud: bool = False
    ):
        """Helper to apply disabled states based on the active flag."""
        
        # ? Console (Always interactive if visible, but we don't disable it via property)
        # ? We just act on the layers below it.
        
        # Settings
        self.settings_menu.disabled = not settings
        
        # Pause Menu
        self.pause_menu.disabled = not pause
        
        # Main Menu
        if self.main_menu:
            self.main_menu.disabled = not main_menu
            
        # Game HUD & Player Control
        self.ui_stack.disabled = not game_hud
        
        # Handle Player Movement Locking
        if self.player:
            # Player can move ONLY if the game HUD is the active focus
            self.player.states.disable_movement = not game_hud
    
    # * === MENU EVENTS ===
    async def start_game(self, _):
        """Switch from Menu to Game"""
        self.main_menu.opacity = 0
        try_update(self.main_menu)
        await self._await_for_dur(self.main_menu)
        self.main_menu.visible = False
        self.main_menu.stop_loop()
        self._remove_main_menu()
        
        self.game_layer.opacity = 0
        self.game_layer.visible = True
        self.ui_stack.disabled = False
        try_update(self.game_layer)
        await asyncio.sleep(0.1)
        self.game_layer.opacity = 1
        self.game_layer.content = self._setup_game_ui()
        try_update(self.game_layer)
        await self._await_for_dur(self.game_layer)
        
        audio_manager.play_music(music.loops.sketchbook.abstraction_2024_03_20_02)
        self.is_game_running = True
        self.start_tasks()
        self._update_ui_focus()
        self._debug_msg("Starting Game!")
        
        if not self.tutorial_handler.finished_tutorial:
            tutorial_dlg = SimpleDialog(
                title="Key Binds Tutorial",
                content="Finish the tutorial first before moving beyond the starting area!"
            )
            self.page.overlay.append(tutorial_dlg)
        self.page.update()
    
    async def open_settings(self, _):
        if self.pause_menu.visible:
            self.pause_menu.visible = False
            self.settings_menu.visible = True
            self.settings_menu.subtitle.visible = True
        
        elif self.main_menu.visible:
            self.settings_menu.visible = True
            self.settings_menu.subtitle.visible = False
        
        self._update_ui_focus()
    
    def close_settings(self, _):
        if self.is_game_running:
            self.pause_menu.visible = True
            self.settings_menu.visible = False
        
        elif self.main_menu.visible:
            self.main_menu.disabled = False
            self.settings_menu.visible = False
        
        self._update_ui_focus()
    
    def toggle_pause(self, _):
        """Toggle Pause Overlay"""
        if not self.is_game_running or self.settings_menu.visible: return
        
        self.pause_menu.visible = not self.pause_menu.visible
        self._update_ui_focus()
        
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
        
        self._make_main_menu()
        self.main_menu.opacity = 0
        self.main_menu.visible = True
        try_update(self.main_menu)
        await asyncio.sleep(0.1)
        audio_manager.play_music(music.loops.sketchbook.abstraction_2023_11_29)
        self.main_menu.opacity = 1
        try_update(self.main_menu)
        await self._await_for_dur(self.main_menu)
        self.main_menu.start_loop()
    
    # * === GAME EVENTS ===
    def summon_enemy(
        self, enemy_type: EnemyType = None,
        spawn_amount: int = None, center_spawn: bool = False
    ) -> list[Entity]:
        """Summons an enemy and returns the list of created instances."""
        
        if enemy_type is None:
            self._debug_msg("Provide an enemy type to summon.")
            return []
            
        if spawn_amount is None: spawn_amount = random.randint(1, 5)
        elif spawn_amount == 0: return []
        else: spawn_amount = abs(spawn_amount)
        
        created_entities = []
        
        self._debug_msg(f"Initial entity_stack size: {len(self.entity_stack.controls)}")
        
        for _ in range(spawn_amount):
            new_entity = None
            match enemy_type:
                # We assign to a variable to append it to our list
                case EnemyType.GOBLIN: 
                    new_entity = NewGoblin(game_manager=self, center_spawn=center_spawn)
                case _: 
                    raise NotImplementedError("Other enemy types are not yet implemented!")
            
            if new_entity:
                created_entities.append(new_entity)
                
        self._debug_msg(f"New entity_stack size: {len(self.entity_stack.controls)}")
        return created_entities
    
    # * === TASK MANAGEMENT ===
    def start_tasks(self) -> None:
        """Starts background loops and appends them to the `running_tasks` list."""
        async def run_light(): await light_mv_loop(self.background_stack)
            
        # Store tasks so we can cancel them later
        self.running_tasks.append(self.page.run_task(run_light))
        if self.tutorial_handler.finished_tutorial:
            self._start_stage_panning()
    
    def _start_stage_panning(self) -> None:
        """Starts the stage panning handler's loop."""
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
        self.running_tasks.append(self.page.run_task(run_pan))
    
    def cleanup(self) -> None:
        """Call this when exiting or changing levels."""
        for task in self.running_tasks: attempt_cancel(task)
        for entity in self.entity_list:
            if isinstance(entity, Enemy):
                entity._cancel_loop_tasks()
                entity._cancel_temp_tasks()
        self.player._cancel_loop_tasks()
        self.player._cancel_temp_tasks()
    
# * === MIXINS ===
class GameManagerMixin:
    """Mixin to bridge GameManager data into Entities."""
    def _configure_from_manager(self: Entity, game_manager: GameManager) -> None:
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
            "audio_manager": audio_manager,
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
        
class NewGoblin(Goblin, GameManagerMixin):
    """
    Wrapped `Enemy` class to be used in the `GameMaker` class.
    Automatically spawns into the scene once called.
    """
    def __init__(
        self, game_manager: GameManager, name: str = None,
        *, center_spawn: bool = True, debug = False
    ) -> None:
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
    def __init__(self, game_manager: GameManager, *, debug = False) -> None:
        self._configure_from_manager(game_manager)
        super().__init__(
            held_keys=held_keys,
            verbose_stamina=game_manager.verbose_stamina,
            **self._get_base_kwargs(debug)
        )
        self._spawn_into_scene()