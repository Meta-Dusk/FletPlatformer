import flet as ft
from pathlib import Path
from typing import Callable
import inspect

from utilities.components import try_update
from audio.audio_manager import global_audio_manager
from audio.sfx_data import SFXLibrary

audio_manager = global_audio_manager
sfx = SFXLibrary()

SwitchState = bool

class CustomSwitch(ft.Container):
    """A switch but square."""
    def __init__(
        self, width: ft.Number = 100, height: ft.Number = 50, value: bool = False,
        on_toggle: Callable[[SwitchState], None] = None
    ):
        self.on_toggle = on_toggle
        self.thumb = ft.Container(
            animate_align=ft.Animation(500, ft.AnimationCurve.EASE_IN_OUT_CUBIC_EMPHASIZED),
            animate=ft.Animation(500, ft.AnimationCurve.EASE_IN_OUT), width=width / 2, height=height,
        )
        
        super().__init__(
            content=self.thumb, width=width, height=height, expand=False, data=value,
            on_click=self._on_click, on_hover=self._on_hover,
            animate=ft.Animation(500, ft.AnimationCurve.EASE_IN_OUT)
        )
        self._toggle_state()
    
    def _toggle_state(self):
        if self.data:
            self.thumb.align = ft.Alignment.CENTER_RIGHT
            self.thumb.bgcolor =ft.Colors.PRIMARY
            self.thumb.border = ft.Border.all(2, ft.Colors.ON_PRIMARY)
            self.bgcolor = ft.Colors.PRIMARY_CONTAINER
            self.border = ft.Border.all(2, ft.Colors.ON_PRIMARY_CONTAINER)
        else:
            self.thumb.align = ft.Alignment.CENTER_LEFT
            self.thumb.bgcolor =ft.Colors.SECONDARY
            self.thumb.border = ft.Border.all(2, ft.Colors.ON_SECONDARY)
            self.bgcolor = ft.Colors.SECONDARY_CONTAINER
            self.border = ft.Border.all(2, ft.Colors.ON_SECONDARY_CONTAINER)
        try_update(self.thumb)
        
        if self.on_toggle:
            result = self.on_toggle(self.data)
            if inspect.isawaitable(result):
                self.page.run_task(result, self.data)
    
    def _play_sfx(self, sfx: Path):
        """Play a sound effect."""
        audio_manager.play_sfx(sfx)
    
    def _on_click(self, _):
        # print(f"Setting CustomSwitch from {self.data} -> ", end="")
        self.data = not self.data
        # print(self.data)
        if self.data: self._play_sfx(sfx.ui.buttons.switch_on)
        else: self._play_sfx(sfx.ui.buttons.switch_off)
        self._toggle_state()
        
    def _on_hover(self, _):
        self._play_sfx(sfx.ui.buttons.hover_1)
        