import flet as ft

from audio.audio_manager import global_audio_manager
from tests.test_templates import test_init
from components.dialog import DialogBox

async def test(page: ft.Page):
    await test_init(page)
    page.bgcolor = ft.Colors.WHITE
    
    color_map = {
        "Narrator": ft.Colors.CYAN
    }
    dialog = DialogBox(
        speaker_name="Narrator",
        dialog_text=[
            "...And so, there was dialog!",
            "This is a dialog box test. Is it working?",
            "Seems to be working... Cool!"
        ],
        speaker_colors=color_map
    )
    
    page.overlay.append(dialog)
    
    
ft.run(test, assets_dir="../assets")