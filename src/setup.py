import asyncio
import flet as ft
from enum import Enum


WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

class FontStyles(Enum):
    """Available font styles."""
    INTER = "Inter"
    LIBRE_CASLON = "Libre Caslon"
    BLRRPIXS = "Blrr Pixs"
    MEDODICA = "Medodica Regular"

def before_main_ui(page: ft.Page):
    """Call before rendering the main UI."""
    page.title = "Flet Platformer Game"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 0
    page.bgcolor = ft.Colors.BLACK
    page.fonts = {
        FontStyles.INTER: "font_styles/Inter-VariableFont_opsz,wght.ttf",
        FontStyles.LIBRE_CASLON: "font_styles/LibreCaslonText-Regular.ttf",
        FontStyles.BLRRPIXS: "font_styles/blrrpixs016.ttf",
        FontStyles.MEDODICA: "font_styles/MedodicaRegular.otf"
    }
    page.theme = ft.Theme(font_family=FontStyles.BLRRPIXS, color_scheme_seed=ft.Colors.BLACK)
    
    page.window.title_bar_hidden = True
    page.window.width = WINDOW_WIDTH
    page.window.height = WINDOW_HEIGHT
    page.window.full_screen = False
    page.window.minimized = False
    page.window.maximized = False
    
async def fix_stretched_window(page: ft.Page, *, center_page: bool = False):
    """
    When launching a Flet desktop app, sometimes the window appears to be stretched.
    The fix? Just resize it. So, that's exactly what this does.
    """
    page.window.width = WINDOW_WIDTH * 1.1
    page.window.height = WINDOW_HEIGHT * 1.1
    page.window.update()
    await asyncio.sleep(1)
    page.window.width = WINDOW_WIDTH
    page.window.height = WINDOW_HEIGHT
    page.window.update()
    if center_page: await page.window.center()