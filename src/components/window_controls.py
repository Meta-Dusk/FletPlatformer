import flet as ft
from typing import Callable, Self

from components.custom_switches import CustomSwitch
from setup import FontStyles


class FullscreenToggle(ft.Container):
    def __init__(self):
        self.switch = CustomSwitch(value=False)
        label = ft.Container(
            content=ft.Text(
                "Borderless Fullscreen", size=30,
                font_family=FontStyles.ADAPA, color=ft.Colors.WHITE_70
            ),
            alignment=ft.Alignment.CENTER, offset=ft.Offset(-0.1, 0.0)
        )
        spacer = ft.Container(width=30)
        
        main_container = ft.Container(
            content=ft.Row(
                controls=[label, spacer, self.switch], expand=True,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
            alignment=ft.Alignment.CENTER
        )
        
        super().__init__(
            content=main_container, alignment=ft.Alignment.CENTER,
            padding=4, expand=True
        )
        self._update_callback: Callable[[Self], None] = None
    
    def did_mount(self):
        self.update()
        self.switch.on_toggle = self._on_toggle
        self._update_callback = self._update_data
    
    def _on_toggle(self, data: bool):
        self.page.window.maximized = data
    
    def _update_data(self):
        print(f"Setting data: {self.switch.data} -> {self.page.window.maximized}")
        self.switch.data = self.page.window.maximized
    
    def update(self):
        if self._update_callback: self._update_callback()
        self.switch._toggle_state()
        super().update()