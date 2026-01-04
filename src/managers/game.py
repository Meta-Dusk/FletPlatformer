import flet as ft
import asyncio, random
from pynput import keyboard

from audio.audio_manager import global_audio_manager as audio_manager
from audio.music_data import MusicLibrary

from components.menus import PauseMenu, SettingsMenu, MainMenu
from components.displays import StatsDisplay, CreateCounter
from components.custom_switches import TextAndToggle
from components.popups import SimpleDialog

import utilities.keyboard_manager as kb_manager
from utilities.components import try_update, await_for_dur
from utilities.commands.ui import DevConsole
from utilities.commands.in_game import GameCommands
from utilities.performance_monitor import PerformanceMonitor
from utilities.tutorial_handler import TutorialHandler

from entities.enemy import EnemyType
from entities.entity import Entity
from entities.player import Player, PlayerType

from bg_loops import LightMovementLoop, StagePanningLoop
from backgrounds import add_infinite_layer

from managers.menu import MenuManager
from managers.settings import SettingsManager
from managers.game_mixins import NewPlayer, NewEnemy
from managers.game_loop import GameLoop

music = MusicLibrary()

class GameManager(GameCommands, MenuManager, SettingsManager):
    """Central hub for the game UI and states."""
    def __init__(self, page: ft.Page) -> None:
        # State Variables (References)
        self.page: ft.Page = page
        self.player: Player = None
        
        # UI Layers
        self.background_stack = ft.Stack(expand=True, alignment=ft.Alignment.CENTER)
        self.foreground_stack = ft.Stack(expand=True, alignment=ft.Alignment.CENTER)
        self.entity_stack = ft.Stack(expand=True, alignment=ft.Alignment.CENTER)
        self.projectile_stack = ft.Stack(expand=True, alignment=ft.Alignment.CENTER)
        self.ui_stack = ft.Stack(expand=True, alignment=ft.Alignment.CENTER)
        self.stage = ft.Stack(expand=True, alignment=ft.Alignment.CENTER)
        self.game_stage = ft.Stack(expand=True, alignment=ft.Alignment.CENTER)
        self.entity_list: list[Entity] = []
        self.console = DevConsole()
        self.stats_panel: StatsDisplay = None
        self.tutorial_handler = TutorialHandler(self.page, self._on_finish_tutorial)
        
        # Task Management
        self.running_tasks: list[asyncio.Task] = []
        self.last_input_time: float = 0.0
        self.light_mv_loop = LightMovementLoop(self.background_stack)
        self.stage_panning_loop = StagePanningLoop(self, self.projectile_stack, self.summon_enemies)
        
        # World Configuration
        self._ground_level: int = 30
        self.is_game_running: bool = False
        
        # Properties
        self._show_borders: bool = False
        self._death_count: int = 0
        self._kill_count: int = 0
        
        # Other Settings
        self.verbose_stamina: bool = False
        
        # Scenes
        self.main_menu: MainMenu = None
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
    def ground_level(self) -> int:
        return self._ground_level
    
    @ground_level.setter
    def ground_level(self, level: int) -> None:
        self._ground_level = level
    
    @property
    def show_borders(self) -> bool:
        return self._show_borders
    
    @show_borders.setter
    def show_borders(self, enabled: bool) -> None:
        self._show_borders = enabled
        self.game_loop.projectile_manager.debug = enabled
    
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
            self.kill_count_text.set_val(amount)
    
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
            self.death_count_text.set_val(amount)
    
    # * === IMPORTANT METHODS ===
    async def __call__(self) -> None:
        """An alternative way to get the main entry point."""
        await self.initialize()
    
    async def initialize(self) -> None:
        """The entry point called by Flet."""
        # --- Setup ---
        audio_manager.play_music(music.loops.sketchbook.abstraction_2023_11_29)
        self.register_commands()
        
        kb_manager.start()
        kb_manager.on_press_callback = self._handle_input_press
        
        self.game_loop = GameLoop(
            self.page, self.entity_list, audio_manager,
            ground_level=self.ground_level, debug=self.show_borders
        )
        self.projectile_stack = self.game_loop.projectile_manager.projectile_layer
        
        # --- Event Handlers ---
        # self.page.on_keyboard_event = self._on_keyboard_event
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
        
        @ft.component
        def Root(): return self.stage
        
        # ! Doing this means we have to refactor everything...
        self.page.render(Root)
        
        await self.page.window.center()
        self.page.window.maximized = True
    
    # * === OTHER HELPERS ===
    def _debug_msg(self, msg: str) -> None:
        """A very simple debug logger."""
        print(f"[GameManager] {msg}")
    
    # * === UI SETUP ===
    def _setup_game_ui(self) -> ft.WindowDragArea:
        """Initializes Player, Stacks, and HUD."""
        # Player
        self.player = NewPlayer(self, PlayerType.HERO_KNIGHT)
        self.player.on_death = self._on_player_death
        self.player.on_kill = self._on_player_kill
        self.player.projectile_manager = self.game_loop.projectile_manager
        
        # Stacks/Layers
        def inf_layer(stack: ft.Stack, index: int):
            add_infinite_layer(stack=stack, index=index, page=self.page)
        
        self.background_stack.controls.clear()
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
        self.ui_stack.controls.clear()
        self.ui_stack.controls = [stats_switch, self.stats_panel]
        if (
            not self.tutorial_handler.finished_tutorial and
            not self.tutorial_handler.tutorial in self.ui_stack.controls
        ):
            self.ui_stack.controls.insert(0, self.tutorial_handler())
        
        self.kill_count_text = CreateCounter("Kills", self.kill_count)
        self.death_count_text = CreateCounter("Deaths", self.death_count)
        self.stats_view = ft.Column(
            controls=[self.kill_count_text, self.death_count_text],
            spacing=4, left=10, top=10,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        )
        
        # Composition
        self.game_stage.controls = [
            self.background_stack,
            self.entity_stack,
            self.projectile_stack,
            self.foreground_stack,
            self.ui_stack,
        ]
        
        form = ft.WindowDragArea(self.game_stage, expand=True, maximizable=False)
        return form
        
    # * === EVENT HANDLERS ===
    def _handle_input_press(self, key_id: kb_manager.KeyType) -> None:
        """
        Runs on the Pynput Thread.
        Direct logic remains here for speed; UI calls are offloaded.
        """
        
        # 1. IMMEDIATE GAME LOGIC (Fast track - No Lag)
        # Perform state changes that don't trigger immediate UI diffing here.
        if self.is_game_running and self.player and not self.player.states.disable_movement:
            if key_id == 'v':
                self.player.attack() # Internal logic/state change
                return
            elif key_id == keyboard.Key.space:
                self.player.jump()
                return
            elif key_id == 'b':
                self.player.attack_ranged()
                return

        # 2. UI & SYSTEM LOGIC (Scheduled - Safe from Crashes)
        # We only offload things that touch self.page or overlays.
        async def ui_press_logic():
            match key_id:
                case keyboard.Key.esc:
                    if self.console.visible:
                        await self._toggle_console()
                    elif self.settings_menu.visible:
                        self.close_settings(None)
                    else:
                        for ctrl in self.page.overlay:
                            if isinstance(ctrl, ft.AlertDialog): return
                        self.toggle_pause(None)

                case "/":
                    if self.console in self.page.overlay:
                        await self._toggle_console()

                case keyboard.Key.f11:
                    self.page.window.maximized = not self.page.window.maximized
            
            # Only update the UI if we actually need to sync changes
            self.page.update()
            self.page.run_task(self.console.handle_keyboard, key_id)

        # Schedule the UI-heavy stuff without blocking the Pynput thread
        self.page.run_task(ui_press_logic)
                
    async def _toggle_console(self):
        await self.console.toggle()
        self._update_ui_focus()
    
    def _on_finish_tutorial(self) -> None:
        """Removes the tutorial controls after finishing the tutorial."""
        self._debug_msg("Finished tutorial!")
        self._start_stage_panning()
        
        if self.tutorial_handler.tutorial in self.ui_stack.controls:
            self.ui_stack.controls.remove(self.tutorial_handler.tutorial)
            
        if not self.stats_view in self.ui_stack.controls:
            self.ui_stack.controls.append(self.stats_view)
            
        tutorial_dlg = SimpleDialog(
            title="Key Binds Tutorial",
            content=[
                "You've finished the tutorial!\n"
                "You can now go ahead an go beyond the starting area.\n"
                "Click outside this message to close it."
            ]
        )
        self.page.overlay.append(tutorial_dlg)
        self.page.update()
    
    def _on_player_death(self) -> None:
        """Incremets the death counter on player death."""
        self.death_count += 1
        self._debug_msg(f"Death count: {self.death_count}")
    
    def _on_player_kill(self) -> None:
        """Increments the kill counter on player kill."""
        self.kill_count += 1
        self._debug_msg(f"Kill Count: {self.kill_count}")
    
    # * === MENU EVENTS ===
    async def start_game(self, _: ft.ControlEvent) -> None:
        """Switch from Menu to Game"""
        # Fade in main menu
        self.main_menu.opacity = 0
        try_update(self.main_menu)
        await await_for_dur(self.main_menu.animate_opacity)
        self.main_menu.visible = False
        self.main_menu.stop_anim_loop()
        self._remove_main_menu()
        
        # Fade in game layer
        self.game_layer.opacity = 0
        self.game_layer.visible = True
        self.ui_stack.disabled = False
        try_update(self.game_layer)
        await asyncio.sleep(0.1)
        self.game_layer.opacity = 1
        self.game_layer.content = self._setup_game_ui()
        try_update(self.game_layer)
        await await_for_dur(self.game_layer.animate_opacity)
        
        # Start the actual game
        audio_manager.play_music(music.loops.sketchbook.abstraction_2024_03_20_02)
        self.is_game_running = True
        self.game_loop.start()
        self.start_tasks()
        self._update_ui_focus()
        self._debug_msg("Starting Game!")
        
        # Check if tutorial is not yet finished
        if not self.tutorial_handler.finished_tutorial:
            tutorial_dlg = SimpleDialog(
                title="Key Binds Tutorial",
                content=[
                    "Finish the tutorial first before moving beyond the starting area!"
                    "\nClick outside this message to close it."
                ]
            )
            self.page.overlay.append(tutorial_dlg)
        self.page.update()
        
    async def quit_to_menu(self, _: ft.ControlEvent) -> None:
        """Cleanup game and show the main menu."""
        # Stop game loop and other tasks
        self.is_game_running = False
        self.game_loop.stop()
        self._stop_running_tasks()
        
        # Animate any open menus and the game menu with fade out
        self.game_layer.opacity = 0
        self.pause_menu.opacity = 0
        self.settings_menu.opacity = 0
        try_update(self.page)
        await await_for_dur(self.game_layer.animate_opacity)
        self.game_layer.content = None
        self.game_layer.visible = False
        self.pause_menu.visible = False
        self.settings_menu.visible = False
        self.pause_menu.opacity = 1
        self.settings_menu.opacity = 1
        try_update(self.page)
        
        # Reset entities and unrender game stage
        self._debug_msg("Quitting to Main Menu! Clearing Entities and Tasks...")
        self.player = None
        self.entity_stack.controls.clear()
        self.entity_list.clear()
        self.game_stage.controls.clear()
        self._debug_msg(f"Previous running tasks: {self.running_tasks}")
        self.running_tasks.clear()
        self._debug_msg(f"player: {self.player}")
        self._debug_msg(f"entity_list: {self.entity_list}")
        self._debug_msg(f"entity_stack: {self.entity_stack.controls}")
        self._debug_msg(f"Running tasks: {self.running_tasks}")
        
        # Make and show the main menu again
        self._make_main_menu()
        self.main_menu.opacity = 0
        self.main_menu.visible = True
        try_update(self.main_menu)
        await asyncio.sleep(0.1)
        audio_manager.play_music(music.loops.sketchbook.abstraction_2023_11_29)
        self.main_menu.opacity = 1
        try_update(self.main_menu)
        await await_for_dur(self.main_menu.animate_opacity)
        self.main_menu.start_anim_loop()
    
    # * === GAME EVENTS ===
    def summon_enemy(
        self, enemy_type: EnemyType = None,
        spawn_amount: int = 1, center_spawn: bool = False, *,
        spawn_range: tuple[int, int] = None
    ) -> list[Entity]:
        """Summons an enemy and returns the list of created instances."""
        
        if enemy_type is None:
            self._debug_msg("Provide an enemy type to summon.")
            return []
            
        if spawn_amount == 0: return []
        elif spawn_amount < 0: raise ValueError("'spawn_amount' cannot be negative!")
        else: spawn_amount = abs(spawn_amount)
        
        if spawn_range: spawn_amount = random.randrange(*spawn_range)
        
        created_entities = []
        
        self._debug_msg(f"Initial entity_stack size: {len(self.entity_stack.controls)}")
        
        for _ in range(spawn_amount):
            new_entity = None
            if enemy_type in EnemyType:
                new_entity = NewEnemy(game_manager=self, type=enemy_type, center_spawn=center_spawn)
            else:
                raise NotImplementedError("Other enemy types are not yet implemented!")
            
            if new_entity: created_entities.append(new_entity)
                
        self._debug_msg(f"New entity_stack size: {len(self.entity_stack.controls)}")
        return created_entities
    
    def summon_enemies(self):
        """A simple test for summoning enemies."""
        self.summon_enemy(EnemyType.GOBLIN, spawn_range=(1, 5))
        self.summon_enemy(EnemyType.FLYING_EYE, spawn_range=(0, 2))
    
    # * === TASK MANAGEMENT ===
    def start_tasks(self) -> None:
        """Starts background loops and appends them to the `running_tasks` list."""
        async def run_light(): await self.light_mv_loop.start()
        self.running_tasks.append(self.page.run_task(run_light))
        
        if self.tutorial_handler.finished_tutorial:
            self._start_stage_panning()
    
    def _start_stage_panning(self) -> None:
        """Starts the stage panning handler's loop."""
        async def run_pan(): await self.stage_panning_loop.start()
        self.running_tasks.append(self.page.run_task(run_pan))
    
    def _stop_running_tasks(self) -> None:
        """Stops all background running tasks."""
        self._debug_msg("Stopping 'light_mv_loop'")
        self.light_mv_loop.stop()
        
        self._debug_msg("Stopping 'stage_panning_loop'")
        self.stage_panning_loop.stop()
        