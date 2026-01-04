import flet as ft
from typing import Optional
import inspect

from audio.audio_manager import global_audio_manager
from audio.sfx_data import SFXLibrary
from setup import FontStyles

sfx = SFXLibrary()

@ft.control
class SimpleButton(ft.Button):
    # --- Define Fields for the Automatic Dataclass Constructor ---
    user_on_click: Optional[ft.ControlEventHandler] = None
    user_on_hover: Optional[ft.ControlEventHandler] = None
    user_on_focus: Optional[ft.ControlEventHandler] = None
    
    on_click_sfx: str = sfx.ui.buttons.item_select
    on_hover_sfx: str = sfx.ui.buttons.hover_1
    on_focus_sfx: str = sfx.ui.buttons.hover_1
    
    font_family: str = FontStyles.ADAPA
    
    def init(self):
        """Custom initialization logic (called after the dataclass __init__)"""
        # Wire up Flet's internal handlers to our custom logic
        self.on_click = self._on_click
        self.on_focus = self._on_focus
        self.on_hover = self._on_hover
        
        # Apply visual styling
        self.style = ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(
                side=ft.BorderSide(color=ft.Colors.WHITE),
                radius=0
            )
        )
        
        # Handle child text properties
        if isinstance(self.content, ft.Text):
            self.content.font_family = self.font_family
            # Scale text if height is provided
            if self.content.size is None and self.height and self.height != 0:
                self.content.size = self.height / 2
    
    def _play_sfx(self, sfx: str) -> None:
        """Play a sound effect."""
        global_audio_manager.play_sfx(sfx)
        
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
        