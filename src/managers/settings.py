import flet as ft
from typing import Callable

from components.displays import StatsDisplay
from components.popups import SimpleNotification
from components.menus import SettingsMenu
from utilities.components import try_update
from utilities.commands.ui import DevConsole
from utilities.performance_monitor import PerformanceMonitor
from entities.player import Player

class SettingsManager:
    """A `GameManager` mixin for handling game settings."""
    def __init__(
        self, stats_panel: StatsDisplay, settings_menu: SettingsMenu,
        player: Player, page: ft.Page, console: DevConsole,
        perf_monitor: PerformanceMonitor, verbose_stamina: bool,
        debug_msg: Callable[[str], None] = None,
    ) -> None:
        """Optional init. You don't need to call this inside the `GameManager`."""
        self.stats_panel = stats_panel
        self.settings_menu = settings_menu
        self.player = player
        self.page = page
        self.console = console
        self.perf_monitor = perf_monitor
        self.verbose_stamina = verbose_stamina
        self._debug_msg = debug_msg
    
    def _toggle_stats_panel(self, enabled: bool) -> None:
        """
        Toggles the visibility of the stats panel,
        and updates its contents.
        """
        self.stats_panel.visible = enabled
        self.stats_panel._update_texts()
        try_update(self.stats_panel)
    
    def _win_on_event(self, e: ft.WindowEvent) -> None:
        """Updates controls that reflect the window's properties."""
        match e.type:
            case ft.WindowEventType.MAXIMIZE | ft.WindowEventType.UNMAXIMIZE:
                self.settings_menu.fullscreen_toggle.update()
        self.settings_menu.win_on_update(e)
    
    def _stamina_verbose_toggle(self, enabled: bool) -> None:
        """Toggles the player's stamina verbose toggle."""
        if self.player:
            st_bar = self.player._stamina_bar_stack
            st_bar.verbose = enabled
            st_bar.st_label.current_value = self.player.stats.stamina
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