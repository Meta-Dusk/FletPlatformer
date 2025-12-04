import flet as ft

from components.custom_switches import CustomSwitch
from setup import FontStyles


class ConsoleToggle(ft.Container):
    def __init__(self):
        self.toggle = CustomSwitch(value=False)
        label = ft.Container(
            content=ft.Text(
                "Enable Dev Console", size=30,
                font_family=FontStyles.ADAPA, color=ft.Colors.WHITE_70
            ),
            alignment=ft.Alignment.CENTER, offset=ft.Offset(0.0, 0.0)
        )
        spacer = ft.Container(width=60)
        
        main_container = ft.Container(
            content=ft.Row(
                controls=[label, spacer, self.toggle], expand=True,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
            alignment=ft.Alignment.CENTER
        )
        
        super().__init__(
            content=main_container, alignment=ft.Alignment.CENTER,
            padding=4, expand=True
        )