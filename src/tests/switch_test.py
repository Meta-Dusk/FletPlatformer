import flet as ft

from audio.audio_manager import global_audio_manager
from components.custom_switches import CustomSwitch

audio_manager = global_audio_manager

def test(page: ft.Page):
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    audio_manager.initialize()
    
    page.add(CustomSwitch())

if __name__ == "__main__": ft.run(test, assets_dir="../assets")