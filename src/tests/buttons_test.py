import flet as ft

from setup import FONT_STYLES
from audio.audio_manager import global_audio_manager
from components.buttons import SimpleButton


def test(page: ft.Page):
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.fonts = FONT_STYLES
    
    audio_manager = global_audio_manager
    audio_manager.initialize()
    
    buttons_column = ft.Column()
    for i in range(5):
        buttons_column.controls.append(
            SimpleButton(ft.Text(f"Button {i}", size=30), width=200, height=100)
        )
    
    page.add(buttons_column)

if __name__ == "__main__": ft.run(test, assets_dir="../assets")