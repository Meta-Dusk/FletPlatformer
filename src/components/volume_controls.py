import flet as ft
from typing import Literal, Any

from audio.audio_manager import AudioManager, global_audio_manager

from components.buttons import SimpleButton
from components.custom_switches import NewSwitch

from setup import FontStyles

AudioTypes = Literal["music", "sfx"]

# * --- VolumeControl ---
@ft.component
def VolumeControlComponent(
    initial_value: float,
    audio_type: AudioTypes,
    label: str
)  -> ft.Control:
    # 1. State management: Initialize from the manager's current value
    volume, set_volume = ft.use_state(initial_value)
    
    # 2. Logic: Modification handlers
    def change_volume(delta: float) -> None:
        new_vol = round(volume + delta, 1)
        if 0.0 <= new_vol <= 1.0:
            # Update the underlying logic (AudioManager)
            if audio_type == "music":
                global_audio_manager.music_volume = new_vol
            else:
                global_audio_manager.sfx_volume = new_vol
            set_volume(new_vol)
            
    # 3. UI Helpers
    def make_text(text: str, size: int = 15) -> ft.Text:
        return ft.Text(
            value=text, font_family=FontStyles.ADAPA,
            size=size, text_align=ft.TextAlign.CENTER,
            color=ft.Colors.WHITE_70
        )
    
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
                    user_on_click=lambda _: change_volume(-0.1)
                ),
                SimpleButton(
                    content=make_text("+"), 
                    user_on_click=lambda _: change_volume(0.1)
                ),
            ], spacing=4)
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        expand=True
    )
    
    # 4. Component Tree
    return ft.Container(
        content=main_content,
        padding=4, alignment=ft.Alignment.CENTER
    )


# * --- DirectionalVolumeToggle ---
@ft.component
def DirectionalVolumeToggleComponent(initial_state: bool) -> ft.Control:
    is_on, set_is_on = ft.use_state(initial_state)
    
    def on_toggle(new_state: bool):
        global_audio_manager.directional_sfx = new_state
        set_is_on(new_state)
        
    return ft.Container(
        alignment=ft.Alignment.CENTER,
        padding=4,
        content=ft.Row(
            controls=[
                ft.Text(
                    "Directional Audio", size=30,
                    font_family=FontStyles.ADAPA,
                    color=ft.Colors.WHITE_70
                ),
                ft.Container(width=100), # Spacer
                NewSwitch(
                    initial_value=is_on,
                    on_toggle=on_toggle
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            expand=True
        )
    )

from tests.test_templates import test_init
from audio.audio_manager import AudioManager

async def test(page: ft.Page) -> None:
    await test_init(page)
    
    audio_manager = AudioManager(debug=True)
    
    @ft.component
    def TestView() -> ft.Control:
        return ft.Column(
            controls=[
                DirectionalVolumeToggleComponent(audio_manager.directional_sfx),
                VolumeControlComponent(audio_manager.music_volume, "music", "Music Volume"),
                VolumeControlComponent(audio_manager.sfx_volume, "sfx", "SFX Volume")
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    
    page.render(TestView)

if __name__ == "__main__":
    ft.run(test, assets_dir="../assets")