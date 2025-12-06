import flet as ft

from audio.audio_manager import global_audio_manager
from tests.test_templates import test_init
from components.dialog import DialogBox

async def test(page: ft.Page):
    await test_init(page)
    
    
    
ft.run(test, assets_dir="../assets")