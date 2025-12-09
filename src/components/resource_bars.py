import flet as ft

from entities.features.entity_data import EntityStats, Factions
from utilities.components import try_update

class StaminaBar(ft.Stack):
    def __init__(
        self, stats: EntityStats, *,
        width: ft.Number = 120,
        verbose: bool = False
    ) -> None:
        """A stamina resource bar. Set `verbose` to `True` for numbers."""
        self._verbose: bool = verbose
        
        self.st_bar = ft.ProgressBar(
            value=0.0, scale=ft.Scale(scale_x=-1, scale_y=1),
            color=ft.Colors.GREY_800, bgcolor=ft.Colors.TRANSPARENT, height=5
        )
        st_container = ft.Container(
            content=self.st_bar, width=width,
            border=ft.Border.all(2, ft.Colors.BLACK), border_radius=5,
            bgcolor=ft.Colors.YELLOW, alignment=ft.Alignment.CENTER
        )
        self.st_label = ft.Text(
            color=ft.Colors.BLACK, size=18,
            spans=[
                ft.TextSpan(stats.stamina),
                ft.TextSpan("/"),
                ft.TextSpan(stats.max_stamina)
            ], left=5, top=-3
        )
        
        super().__init__(
            controls=[st_container],
            clip_behavior=ft.ClipBehavior.NONE,
            alignment=ft.Alignment.CENTER
        )
        if self.verbose: self._enable_verbose()
    
    @property
    def verbose(self) -> bool:
        return self._verbose
    
    @verbose.setter
    def verbose(self, toggle: bool) -> None:
        self._verbose = toggle
        self._enable_verbose()
        
    def _enable_verbose(self) -> None:
        """
        If `verbose` is `True`, then the stamina resource bar will show
        numbers, and the bar itself larger.
        """
        if self.verbose:
            self.st_bar.height = 18
            self.controls.append(self.st_label)
        else:
            self.st_bar.height = 5
            self.controls.remove(self.st_label)
        try_update(self)
        
class HealthBar(ft.Stack):
    def __init__(
        self, stats: EntityStats, faction: Factions, *,
        width: ft.Number = 120,
    ) -> None:
        """A health resource bar."""
        
        self.hp_bar = ft.ProgressBar(
            value=0.0, scale=ft.Scale(scale_x=-1, scale_y=1),
            color=ft.Colors.GREY_800, bgcolor=ft.Colors.TRANSPARENT, height=18
        )
        healthbar_container = ft.Container(
            content=self.hp_bar, width=width, border=ft.Border.all(2, ft.Colors.BLACK), border_radius=5,
            bgcolor=ft.Colors.RED if faction == Factions.NONHUMAN else ft.Colors.GREEN
        )
        self.hp_label = ft.Text(
            color=ft.Colors.BLACK, size=18,
            spans=[
                ft.TextSpan(stats.health),
                ft.TextSpan("/"),
                ft.TextSpan(stats.max_health)
            ], left=5, top=-3
        )
        
        super().__init__(
            controls=[healthbar_container, self.hp_label],
            clip_behavior=ft.ClipBehavior.NONE,
            alignment=ft.Alignment.CENTER
        )