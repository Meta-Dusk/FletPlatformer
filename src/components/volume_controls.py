import flet as ft
from typing import Literal

from audio.audio_manager import AudioManager
from components.buttons import SimpleButton
from components.custom_switches import CustomSwitch
from setup import FontStyles
from utilities.components import try_update


class VolumeControl(ft.Container):
    def __init__(
        self, audio_manager: AudioManager,
        audio_type: Literal["music", "sfx"],
        label: str
    ):
        self.audio_manager = audio_manager
        self.audio_type = audio_type
        self.label = label
        
        self.value_container = ft.Container(
            self._make_text(size=30), padding=4,
            alignment=ft.Alignment.CENTER, width=250
        )
        self._update_text()
        
        v_up_btn = SimpleButton(
            self._make_text("+"), on_click=self.on_volume_up
        )
        v_down_btn = SimpleButton(
            self._make_text("-"), on_click=self.on_volume_down
        )
        
        btn_row = ft.Row(
            controls=[v_down_btn, v_up_btn], spacing=4,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        spacer = ft.Container(width=25)
        main_row = ft.Row(
            controls=[self.value_container, spacer, btn_row], spacing=20,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True
        )
        
        super().__init__(
            content=main_row, padding=4,
            alignment=ft.Alignment.CENTER, expand=True
        )
    
    def _update_text(self):
        text: ft.Text = self.value_container.content
        text.value = f"{self.label}: {self._get_volume_from_type()}"
        try_update(self.value_container)
    
    def _make_text(
        self, text: str = "",
        font_family: FontStyles = FontStyles.ADAPA,
        size: ft.Number = 15
    ):
        return ft.Text(
            value=text, font_family=font_family,
            size=size, text_align=ft.TextAlign.CENTER,
            color=ft.Colors.WHITE_70
        )
    
    def _get_volume_from_type(self):
        if self.audio_type == "music": return self.audio_manager.music_volume
        elif self.audio_type == "sfx": return self.audio_manager.sfx_volume
    
    def _modify_volume_from_type(self, volume: float):
        if self.audio_type == "music":
            print(f"Music volume {self._get_volume_from_type()} -> ", end="")
            self.audio_manager.music_volume += volume
        elif self.audio_type == "sfx":
            print(f"SFX volume {self._get_volume_from_type()} -> ", end="")
            self.audio_manager.sfx_volume += volume
        print(self._get_volume_from_type())
    
    def on_volume_up(self, _):
        self._modify_volume_from_type(0.1)
        self._update_text()
            
    def on_volume_down(self, _):
        self._modify_volume_from_type(-0.1)
        self._update_text()
        
class DirectionalVolumeToggle(ft.Container):
    def __init__(
        self, audio_manager: AudioManager
    ):
        self.audio_manager = audio_manager
        toggle = CustomSwitch(value=True, on_toggle=self._on_toggle)
        label = ft.Container(
            content=ft.Text(
                "Directional Audio", size=30,
                font_family=FontStyles.ADAPA,
                color=ft.Colors.WHITE_70
            ),
            alignment=ft.Alignment.CENTER, offset=ft.Offset(0.1, 0.0)
        )
        spacer = ft.Container(width=100)
        
        main_container = ft.Container(
            content=ft.Row(
                controls=[label, spacer, toggle], expand=True,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
            alignment=ft.Alignment.CENTER
        )
        
        super().__init__(
            content=main_container, alignment=ft.Alignment.CENTER,
            padding=4, expand=True
        )
    
    def _on_toggle(self, data: bool):
        self.audio_manager.directional_sfx = data