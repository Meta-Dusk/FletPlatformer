import flet as ft
from pathlib import Path
from typing import Optional
import inspect

from audio.audio_manager import global_audio_manager
from audio.sfx_data import SFXLibrary
from setup import FontStyles

sfx = SFXLibrary()
audio_manager = global_audio_manager

class SimpleButton(ft.Button):
    def __init__(
        self, content: ft.StrOrControl,
        on_click: Optional[ft.ControlEventHandler[ft.Button]] = None,
        on_hover: Optional[ft.ControlEventHandler[ft.Button]] = None,
        on_focus: Optional[ft.ControlEventHandler[ft.Button]] = None,
        on_click_sfx: Path = sfx.ui.buttons.item_select,
        on_hover_sfx: Path = sfx.ui.buttons.hover_1,
        on_focus_sfx: Path = sfx.ui.buttons.hover_1,
        width: ft.Number = None,
        height: ft.Number = None,
        font_family: FontStyles = FontStyles.ADAPA,
        left: ft.Number = None,
        right: ft.Number = None,
        top: ft.Number = None,
        bottom: ft.Number = None,
    ) -> None:
        self.user_on_click = on_click
        self.user_on_hover = on_hover
        self.user_on_focus = on_focus
        self.on_click_sfx = on_click_sfx
        self.on_hover_sfx = on_hover_sfx
        self.on_focus_sfx = on_focus_sfx
        super().__init__(
            content=content,
            on_click=self._on_click,
            # on_hover=self._on_hover,
            on_focus=self._on_focus,
            width=width, height=height,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(
                    side=ft.BorderSide(color=ft.Colors.WHITE),
                    radius=0
                )
            ),
            left=left, right=right, top=top, bottom=bottom
        )
        if isinstance(self.content, ft.Text):
            self.content.font_family = font_family
            if self.content.size is None and height and height != 0:
                self.content.size = height / 2
        
    def _play_sfx(self, sfx: Path) -> None:
        """Play a sound effect."""
        audio_manager.play_sfx(sfx)
        
    async def _on_click(self, e: ft.ControlEvent) -> None:
        """Plays a sound before the `on_click` callback."""
        self._play_sfx(self.on_click_sfx)
        
        if self.user_on_click:
            result = self.user_on_click(e)
            if inspect.isawaitable(result): await result
            
        else:
            if isinstance(self.content, ft.Text):
                print(f"{self.content.value} has been clicked!")
    
    def _on_hover(self, e: ft.ControlEvent) -> None:
        """Plays a sound before the `on_hover` callback."""
        if e.data: self._play_sfx(self.on_hover_sfx)
        if self.user_on_hover: self.user_on_hover(e)
        
    def _on_focus(self, e: ft.ControlEvent) -> None:
        """Plays a sound before the `on_focus` callback."""
        self._play_sfx(self.on_focus_sfx)
        if self.user_on_focus: self.user_on_focus(e)
        