import flet as ft

from entities.features.entity_data import EntityStats, Factions
from utilities.components import try_update

class ResourceLabel(ft.Text):
    def __init__(
        self, value: float, max_value: float, *,
        left: ft.Number = 5, right: ft.Number = None,
        top: ft.Number = -3, bottom: ft.Number = None,
        size: ft.Number = 18
    ) -> None:
        self._current_value = value
        self._max_value = max_value
        
        super().__init__(
            color=ft.Colors.BLACK, size=size,
            spans=[
                ft.TextSpan(self.current_value),
                ft.TextSpan("/"),
                ft.TextSpan(self.max_value)
            ],
            left=left, right=right, top=top, bottom=bottom
        )
    
    def _update_text(self, span_index: int = 0, new_value: float = 0.0) -> None:
        self.spans[span_index].text = new_value
        try_update(self)
    
    @property
    def current_value(self) -> float:
        return self._current_value
    
    @current_value.setter
    def current_value(self, value: float) -> None:
        self._current_value = value
        self._update_text(0, value)
    
    @property
    def max_value(self) -> float:
        return self._max_value
    
    @max_value.setter
    def max_value(self, max_value: float) -> None:
        self._max_value = max_value
        self._update_text(2, max_value)

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
        self.st_label = ResourceLabel(stats.stamina, stats.max_stamina)
        
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
            if not self.st_label in self.controls:
                self.controls.append(self.st_label)
        else:
            self.st_bar.height = 5
            if self.st_label in self.controls:
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
        self.hp_label = ResourceLabel(stats.health, stats.max_health)
        
        super().__init__(
            controls=[healthbar_container, self.hp_label],
            clip_behavior=ft.ClipBehavior.NONE,
            alignment=ft.Alignment.CENTER
        )