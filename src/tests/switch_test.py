import flet as ft

from audio.audio_manager import global_audio_manager
from components.custom_switches import CustomSwitch
from tests.test_templates import test_init

audio_manager = global_audio_manager

async def test(page: ft.Page):
    await test_init(page)
    
    audio_manager.initialize()
    
    page.add(CustomSwitch())

ft.run(test, assets_dir="../assets")