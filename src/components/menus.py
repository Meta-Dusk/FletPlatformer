import flet as ft
from typing import Optional
from pathlib import Path

from setup import FontStyles
from components.custom_buttons import NinePatchButton


SCRIPT_DIR = Path(__file__).parent.parent.resolve()
BTN_IMG_PATH = SCRIPT_DIR / "assets" / "images" / "ui" / "buttons" / "UI_Flat_Button02a_4.png"

def pixel_button(text: str, on_click: ft.ControlEventHandler = None):
    pixel_btn_txt = ft.Text(
        value=text, font_family=FontStyles.ADAPA,
        size=40, color=ft.Colors.BLACK
    )
    return NinePatchButton(
        src=BTN_IMG_PATH, width=240, height=80,
        content=pixel_btn_txt, on_click=on_click,
        color=ft.Colors.ORANGE
    )

def btn_txt(text: str):
    return ft.Text(
        value=text, size=30, font_family=FontStyles.ADAPA
    )

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
                    ft.Text("Flet Platformer", size=80, font_family=FontStyles.DUNGEON),
                    ft.Container(height=10),
                    ft.Button(btn_txt("Start Game"), on_click=on_start),
                    ft.Button(btn_txt("Quit"), on_click=on_quit),
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
                    ft.Text("PAUSED", size=80, font_family=FontStyles.MEDODICA),
                    ft.Button(btn_txt("Resume"), on_click=on_resume),
                    ft.Button(btn_txt("Quit to Title"), on_click=on_quit),
                ], alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        )