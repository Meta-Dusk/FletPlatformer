import flet as ft

from audio.audio_manager import global_audio_manager
from tests.test_templates import test_init
from components.menus import NewSettingsMenu

async def test(page: ft.Page):
    await test_init(page)
    page.bgcolor = ft.Colors.WHITE
    
    def on_close(_) -> None:
        print("Settings Closed")
        
    # In 0.80.1+, `page.render` takes the FUNCTION and its arguments
    # This triggers the reactive hooks correctly.
    page.render(
        NewSettingsMenu, 
        audio_manager=global_audio_manager, 
        on_close=on_close
    )

ft.run(test, assets_dir="../assets")