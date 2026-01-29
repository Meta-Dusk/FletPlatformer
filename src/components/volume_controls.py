import flet as ft
from typing import Literal

from audio.audio_manager import global_audio_manager as audio_manager

from components.buttons import SimpleButton
from components.custom_switches import NewTextAndToggle

from setup import FontStyles

AudioTypes = Literal["music", "sfx"]

# * --- VolumeControl ---
@ft.component
def VolumeControlComponent(
    initial_value: float,
    audio_type: AudioTypes,
    label: str
)  -> ft.Control:
    # State management: Initialize from the manager's current value
    volume, set_volume = ft.use_state(initial_value)
    
    # Logic: Modification handlers
    def change_volume(delta: float) -> None:
        new_vol = round(volume + delta, 1)
        if 0.0 <= new_vol <= 1.0:
            if audio_type == "music":
                audio_manager.music_volume = new_vol
            else:
                audio_manager.sfx_volume = new_vol
            set_volume(new_vol)
            
    # UI Helpers
    def make_text(text: str, size: int = 15) -> ft.Text:
        return ft.Text(
            value=text, font_family=FontStyles.ADAPA,
            size=size, text_align=ft.TextAlign.CENTER,
            color=ft.Colors.WHITE_70
        )
    
    # Component Tree
    main_content = ft.Row(
        controls=[
            # Value Display
            ft.Container(
                content=make_text(f"{label}: {volume}", 30),
                width=250, alignment=ft.Alignment.CENTER
            ),
            ft.Container(width=25), # Spacer
            # Controls
            ft.Row([
                SimpleButton(
                    content=make_text("-"),
                    on_click=lambda _: change_volume(-0.1)
                ),
                SimpleButton(
                    content=make_text("+"), 
                    on_click=lambda _: change_volume(0.1)
                ),
            ], spacing=4)
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True
    )
    
    return ft.Container(
        content=main_content,
        padding=4, alignment=ft.Alignment.CENTER
    )


# * --- DirectionalVolumeToggle ---
@ft.component
def DirectionalVolumeToggleComponent(initial_state: bool, *, debug: bool = False) -> ft.Control:
    is_on, set_is_on = ft.use_state(initial_state)
    
    def on_toggle(new_state: bool):
        if debug:
            prev_state = audio_manager.directional_sfx
            print(f"[AudioManager -> Event] Toggling directional SFX from {prev_state} to {new_state}")
        audio_manager.directional_sfx = new_state
        set_is_on(new_state)
        
    return ft.Container(
        alignment=ft.Alignment.CENTER,
        padding=4,
        content=ft.Row(
            controls=[
                NewTextAndToggle(
                    "Directional Audio", switch_value=is_on, on_toggle=on_toggle,
                    spacer_width=80, label_offset=ft.Offset(0.1, 0)
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True
        )
    )


# * Volume Controls Test
from tests.test_templates import test_init
from audio.music_data import MusicLibrary

async def test(page: ft.Page) -> None:
    await test_init(page)
    music = MusicLibrary()
    
    @ft.component
    def TestView() -> ft.Control:
        return ft.Column(
            controls=[
                ft.Text("Volume Controls", size=30),
                DirectionalVolumeToggleComponent(audio_manager.directional_sfx, debug=True),
                VolumeControlComponent(audio_manager.music_volume, "music", "Music Volume"),
                VolumeControlComponent(audio_manager.sfx_volume, "sfx", "SFX Volume"),
                SimpleButton("Play Some Music", on_click=lambda _: audio_manager.play_music(music.ambience.forest))
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    
    page.render(TestView)

if __name__ == "__main__": ft.run(test, assets_dir="../assets")