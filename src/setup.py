import flet as ft
from enum import Enum

class FontStyles(Enum):
    """Available font styles."""
    INTER = "Inter"
    LIBRE_CASLON = "Libre Caslon"
    BLRRPIXS = "Blrr Pixs"
    MEDODICA = "Medodica Regular"
    ADAPA = "Adapa"
    DUNGEON = "Dungeon Font"
    LIEF = "Lief"

FONT_STYLES = {
    FontStyles.INTER: "font_styles/Inter-VariableFont_opsz,wght.ttf",
    FontStyles.LIBRE_CASLON: "font_styles/LibreCaslonText-Regular.ttf",
    FontStyles.BLRRPIXS: "font_styles/blrrpixs016.ttf",
    FontStyles.MEDODICA: "font_styles/MedodicaRegular.otf",
    FontStyles.ADAPA: "font_styles/Adapa.otf",
    FontStyles.DUNGEON: "font_styles/DungeonFont.ttf",
    FontStyles.LIEF: "font_styles/Lief.ttf",
}

def before_main_ui(page: ft.Page):
    """Call before rendering the main UI."""
    page.title = "Flet Platformer Game"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 0
    page.bgcolor = ft.Colors.BLACK
    page.fonts = FONT_STYLES
    page.theme = ft.Theme(font_family=FontStyles.LIEF, color_scheme_seed=ft.Colors.BLACK)
    
    page.window.title_bar_hidden = True
    page.window.full_screen = False
    page.window.minimized = False
    page.window.maximized = False
    