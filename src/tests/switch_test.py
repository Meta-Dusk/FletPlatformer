import flet as ft

from audio.audio_manager import global_audio_manager
from components.custom_switches import NewSwitch
from tests.test_templates import test_init

audio_manager = global_audio_manager

async def test(page: ft.Page):
    await test_init(page)
    page.render(NewSwitch)

ft.run(test, assets_dir="../assets")