import flet as ft
import asyncio, inspect
from typing import Callable

from utilities.tasks import attempt_cancel
from setup import FontStyles
from audio.audio_manager import global_audio_manager
from audio.sfx_data import SFXLibrary

audio_manager = global_audio_manager
sfx = SFXLibrary()

class DialogBox(ft.Container):
    def __init__(
        self, 
        speaker_name: str | list[str] = "Insert name",
        dialog_text: str | list[str] = "Insert message", 
        speaker_colors: dict[str, ft.ColorValue] = None,
        *,
        char_anim_duration: float = 0.05,
        indicator_blink_duration: int = 300,
        cleanup: bool = True,
        on_finish: Callable[[None], None] = lambda: print("Finished dialog.")
    ) -> None:
        """
        A visual novel styled dialog box.
        
        Args:
            speaker_name (str | list[str]): If a list is provided, each dialog is mapped per item in the list. If only
                                            one name is provided, it will be the only speaker.
            dialog_text (str | list[str]): Each string is treated as its own dialog sequence.
            speaker_colors (dict[str, str]): Color mapping for each `speaker_name`.
            char_anim_duration (float): The animation duration (in seconds) per character.
            indicator_blink_duration (int): The animation duration (in milliseconds) for the blink indicator.
            cleanup (bool): If `True`, removes self from the page's overlay.
            on_finish (Callable[[None], None]): Calls this function once the dialog is finished.
        """
        
        # --- 1. Normalize Inputs to Lists ---
        if isinstance(dialog_text, str):
            self.dialog_lines = [dialog_text]
        else:
            self.dialog_lines = dialog_text
            
        if isinstance(speaker_name, str):
            self.speaker_names = [speaker_name] * len(self.dialog_lines)
        else:
            self.speaker_names = speaker_name
            if len(self.speaker_names) < len(self.dialog_lines):
                self.speaker_names.extend(["???"] * (len(self.dialog_lines) - len(self.speaker_names)))

        # Color Mapping (Default to empty dict if None)
        self.speaker_colors = speaker_colors if speaker_colors else {}

        # State Tracking
        self._current_idx: int = 0
        self.char_anim_duration = char_anim_duration
        self._anim_text_task: asyncio.Task = None
        self._anim_ind_task: asyncio.Task = None
        self.cleanup = cleanup
        self.on_finish = on_finish
        
        # --- UI Setup ---
        self.name_text = ft.Text(self.speaker_names[0], size=35)
        
        speaker_container = ft.Container(
            content=ft.Row(
                controls=[self.name_text],
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True
            ),
            alignment=ft.Alignment.CENTER, height=50
        )
        
        self.dialog_text = ft.Text("", size=30, font_family=FontStyles.ADAPA)
        dialog_container = ft.Container(
            content=self.dialog_text,
            alignment=ft.Alignment.CENTER, expand=True,
        )
        
        dialog_col = ft.Column(
            controls=[
                speaker_container,
                ft.Divider(color=ft.Colors.GREY),
                dialog_container
            ],
            spacing=0,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        self.indicator = ft.Container(
            ft.Text(">", size=40, color=ft.Colors.ORANGE),
            alignment=ft.Alignment.CENTER,
            bottom=20, right=20, opacity=0,
            animate_opacity=ft.Animation(indicator_blink_duration, ft.AnimationCurve.LINEAR)
        )
        
        main_stack = ft.Stack(
            controls=[dialog_col, self.indicator],
            expand=True, clip_behavior=ft.ClipBehavior.NONE
        )
        
        super().__init__(
            content=main_stack, bottom=10, left=10, right=10, height=300,
            bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.BLACK),
            on_click=self._on_click,
            border=ft.border.all(2, ft.Colors.WHITE_24),
            border_radius=10
        )
    
    @property
    def current_msg(self) -> str:
        """Returns the full string of the current line."""
        return self.dialog_lines[self._current_idx]

    def _on_click(self, _) -> None:
        """State machine for handling clicks."""
        audio_manager.play_sfx(sfx.ui.buttons.click_1)
        
        if self._anim_text_task and not self._anim_text_task.done():
            attempt_cancel(self._anim_text_task)
            return

        if self._current_idx < len(self.dialog_lines) - 1:
            self._current_idx += 1
            self._start_dialog_sequence()
        else:
            self.visible = False
            attempt_cancel(self._anim_ind_task)
            attempt_cancel(self._anim_text_task)
            if self.cleanup:
                print(f"Cleaning up dialog box from page overlay: {len(self.page.overlay)} -> ", end="")
                self.page.overlay.remove(self)
                print(len(self.page.overlay))
                self.page.update()
            else:
                self.update()
                self._on_finish()
    
    def _start_dialog_sequence(self):
        """Resets UI for the current index and starts animation tasks."""
        # Update Speaker Name
        current_name = self.speaker_names[self._current_idx]
        self.name_text.value = current_name
        
        # --- NEW COLOR LOGIC ---
        # Look up the name in the dictionary. Default to White if not found.
        if current_name in self.speaker_colors:
            self.name_text.color = self.speaker_colors[current_name]
        else:
            self.name_text.color = ft.Colors.WHITE
        
        self.name_text.update()
        
        # Reset Dialog Text & Indicator
        self.dialog_text.value = ""
        self.indicator.opacity = 0
        self.update() 
        
        # Restart Tasks
        attempt_cancel(self._anim_text_task)
        attempt_cancel(self._anim_ind_task)
        
        self._anim_text_task = self.page.run_task(self._animate_text)
        self._anim_ind_task = self.page.run_task(self._animate_indicator)

    async def _animate_indicator(self):
        try:
            while True:
                if self._anim_text_task and not self._anim_text_task.done():
                    await asyncio.sleep(0.1)
                    continue
                
                duration = round(self.indicator.animate_opacity.duration / 1000, 3)
                self.indicator.opacity = 1
                self.indicator.update()
                await asyncio.sleep(duration)
                self.indicator.opacity = 0
                self.indicator.update()
                await asyncio.sleep(duration)
        except asyncio.CancelledError:
            self.indicator.opacity = 0
            self.indicator.update()
    
    async def _animate_text(self):
        full_text = self.current_msg
        try:
            self.dialog_text.value = ""
            for char in full_text:
                self.dialog_text.value += char
                self.dialog_text.update()
                await asyncio.sleep(self.char_anim_duration)
        except asyncio.CancelledError:
            self.dialog_text.value = full_text
            self.dialog_text.update()
    
    def _on_finish(self):
        result = self.on_finish()
        if inspect.isawaitable(result):
            self.page.run_task(result)
    
    def did_mount(self):
        self._start_dialog_sequence()
    
    def will_unmount(self):
        attempt_cancel(self._anim_ind_task)
        attempt_cancel(self._anim_text_task)
        self._on_finish()
    
    def set_new_conversation(
        self, 
        names: str | list[str], 
        msgs: str | list[str],
        colors: dict[str, str] = None
    ) -> None:
        """Resets the dialog box with a completely new conversation."""
        if isinstance(msgs, str):
            self.dialog_lines = [msgs]
        else:
            self.dialog_lines = msgs
            
        if isinstance(names, str):
            self.speaker_names = [names] * len(self.dialog_lines)
        else:
            self.speaker_names = names
        
        # Update colors if provided
        if colors:
            self.speaker_colors = colors
            
        self._current_idx = 0
        self.visible = True
        self.update()
        self._start_dialog_sequence()