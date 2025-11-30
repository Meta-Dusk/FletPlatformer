import flet as ft
from typing import Optional

from setup import FontStyles


class MainMenu(ft.Container):
    def __init__(
        self,
        on_start: Optional[ft.ControlEventHandler[ft.Button]] = None,
        on_quit: Optional[ft.ControlEventHandler[ft.Button]] = None
    ):
        super().__init__(
            expand=True, bgcolor=ft.Colors.BLACK, alignment=ft.Alignment.CENTER,
            content=ft.Column(
                controls=[
                    ft.Text("Flet Platformer", size=50, weight=ft.FontWeight.BOLD, font_family=FontStyles.MEDODICA),
                    ft.Button("Start Game", on_click=on_start),
                    ft.Button("Quit", on_click=on_quit),
                ], alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        )

class PauseMenu(ft.Container):
    def __init__(
        self,
        on_resume: Optional[ft.ControlEventHandler[ft.Button]] = None,
        on_quit: Optional[ft.ControlEventHandler[ft.Button]] = None
    ):
        super().__init__(
            expand=True, visible=False,
            bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                controls=[
                    ft.Text("PAUSED", size=40, font_family=FontStyles.MEDODICA),
                    ft.Button("Resume", on_click=on_resume),
                    ft.Button("Quit to Title", on_click=on_quit),
                ], alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        )