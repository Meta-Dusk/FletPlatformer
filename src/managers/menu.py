import flet as ft
from typing import Callable, Awaitable

from utilities.commands.ui import DevConsole
from utilities.components import try_update
from components.menus import SettingsMenu, PauseMenu, MainMenu
from entities.player import Player

class MenuManager:
    """A `GameManager` mixin for handling menus."""
    def __init__(
        self, console: DevConsole, page: ft.Page,
        settings_menu: SettingsMenu, pause_menu: PauseMenu, main_menu: MainMenu,
        is_game_running: bool, player: Player,
        ui_stack: ft.Stack, game_layer: ft.Container, stage: ft.Stack,
        debug_msg: Callable[[str], None] = None,
        start_game: Callable[[ft.ControlEvent], Awaitable[None]] = None
    ) -> None:
        """Optional init. You don't need to call this inside the `GameManager`."""
        self.console = console
        self.page = page
        self.settings_menu = settings_menu
        self.pause_menu = pause_menu
        self.main_menu = main_menu
        self.is_game_running = is_game_running
        self.player = player
        self.ui_stack = ui_stack
        self.game_layer = game_layer
        self.stage = stage
        self._debug_msg = debug_msg
        self.start_game = start_game
    
    # * === COMPONENT METHODS ===
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
    
    def _remove_main_menu(self) -> None:
        """Removes the Main Menu."""
        self.stage.controls.remove(self.main_menu)
        try_update(self.stage)
    
    # * === UI MANAGEMENT ===
    def _update_ui_focus(self) -> None:
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
    ) -> None:
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
    
    # * === MENU CALLBACKS ===
    async def open_settings(self, _: ft.ControlEvent) -> None:
        if self.pause_menu.visible:
            self.pause_menu.visible = False
            self.settings_menu.visible = True
            self.settings_menu.subtitle.visible = True
        
        elif self.main_menu.visible:
            self.settings_menu.visible = True
            self.settings_menu.subtitle.visible = False
        
        self._update_ui_focus()
    
    def close_settings(self, _: ft.ControlEvent) -> None:
        if self.is_game_running:
            self.pause_menu.visible = True
            self.settings_menu.visible = False
        
        elif self.main_menu.visible:
            self.main_menu.disabled = False
            self.settings_menu.visible = False
        
        self._update_ui_focus()
    
    def toggle_pause(self, _: ft.ControlEvent) -> None:
        """Toggle Pause Overlay"""
        if not self.is_game_running or self.settings_menu.visible: return
        
        self.pause_menu.visible = not self.pause_menu.visible
        self._update_ui_focus()
        
        msg = "Game paused!" if self.pause_menu.visible else "Unpausing game!"
        self._debug_msg(msg)