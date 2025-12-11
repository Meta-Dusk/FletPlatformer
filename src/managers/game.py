import flet as ft
import asyncio, random

from audio.audio_manager import global_audio_manager
from audio.music_data import MusicLibrary

from components.menus import PauseMenu, SettingsMenu
from components.displays import StatsDisplay
from components.custom_switches import TextAndToggle
from components.popups import SimpleDialog

from utilities.keyboard_manager import start as km_start
from utilities.tasks import attempt_cancel
from utilities.components import try_update, await_for_dur
from utilities.commands.ui import DevConsole
from utilities.commands.in_game import GameCommands
from utilities.performance_monitor import PerformanceMonitor
from utilities.tutorial_handler import TutorialHandler

from entities.enemy import EnemyType, Enemy
from entities.entity import Entity
from entities.player import Player, PlayerType

from bg_loops import light_mv_loop, stage_panning_loop
from backgrounds import add_infinite_layer

from managers.menu import MenuManager
from managers.settings import SettingsManager
from managers.game_mixins import NewPlayer, NewEnemy

music = MusicLibrary()
audio_manager = global_audio_manager

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
        self._ground_level: int = 30
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
    
    # * === UI SETUP ===
    def _setup_game_ui(self) -> ft.WindowDragArea:
        """Initializes Player, Stacks, and HUD."""
        # Player
        self.player = NewPlayer(self, PlayerType.HERO_KNIGHT)
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
    async def _on_keyboard_event(self, e: ft.KeyboardEvent) -> None:
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
            content="""You've finished the tutorial!
You can now go ahead an go beyond the starting area.
Click outside this message to close it."""
        )
        self.page.overlay.append(tutorial_dlg)
        self.ui_stack.update()
    
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
        self.main_menu.opacity = 0
        try_update(self.main_menu)
        await await_for_dur(self.main_menu.animate_opacity)
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
        await await_for_dur(self.game_layer.animate_opacity)
        
        audio_manager.play_music(music.loops.sketchbook.abstraction_2024_03_20_02)
        self.is_game_running = True
        self.start_tasks()
        self._update_ui_focus()
        self._debug_msg("Starting Game!")
        
        if not self.tutorial_handler.finished_tutorial:
            tutorial_dlg = SimpleDialog(
                title="Key Binds Tutorial",
                content="""Finish the tutorial first before moving beyond the starting area!
Click outside this message to close it."""
            )
            self.page.overlay.append(tutorial_dlg)
        self.page.update()
        
    async def quit_to_menu(self, _: ft.ControlEvent) -> None:
        """Cleanup game and show menu"""
        self.is_game_running = False
        self.cleanup()
        
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
        await await_for_dur(self.main_menu.animate_opacity)
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
                    new_entity = NewEnemy(game_manager=self, type=enemy_type, center_spawn=center_spawn)
                case _: 
                    raise NotImplementedError("Other enemy types are not yet implemented!")
            
            if new_entity: created_entities.append(new_entity)
                
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
    