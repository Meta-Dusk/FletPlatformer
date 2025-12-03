import flet as ft

from audio.audio_manager import global_audio_manager
from components.buttons import SimpleButton
from tests.test_templates import test_init


async def test(page: ft.Page):
    await test_init(page)
    
    audio_manager = global_audio_manager
    audio_manager.initialize()
    
    buttons_column = ft.Column()
    for i in range(5):
        buttons_column.controls.append(
            SimpleButton(ft.Text(f"Button {i}", size=20), width=200, height=100)
        )
        
    page.add(buttons_column)

ft.run(test, assets_dir="../assets")