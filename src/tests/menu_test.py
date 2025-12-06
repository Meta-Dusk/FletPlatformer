import flet as ft

from audio.audio_manager import global_audio_manager
from tests.test_templates import test_init
from components.menus import SettingsMenu


async def test(page: ft.Page):
    await test_init(page)
    page.bgcolor = ft.Colors.WHITE
    
    settings_menu = SettingsMenu(global_audio_manager)
    settings_menu.visible = True
    
    page.add(settings_menu)

ft.run(test, assets_dir="../assets")