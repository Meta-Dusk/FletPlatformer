import flet as ft
from typing import Callable, Optional
import inspect

from audio.audio_manager import global_audio_manager as audio_manager
from audio.sfx_data import SFXLibrary
from setup import FontStyles

sfx = SFXLibrary()

SwitchEventCallable = Optional[Callable[[bool], None]]

# * --- CustomSwitch ---
@ft.control(kw_only=True)
class CustomSwitch(ft.Container):
    # Defining these fields here gives you IDE autocompletion
    width: ft.Number = 100
    height: ft.Number = 50
    initial_value: bool = False
    on_toggle: SwitchEventCallable = None

    def init(self):
        # We store the setter in a standard attribute for the component to use
        self.toggle_state: Callable[[bool], None] = lambda _: None

@ft.component
def CustomSwitchComponent(control: CustomSwitch) -> ft.Control:
    # 1. Reactive State
    is_on, set_is_on = ft.use_state(control.initial_value)
    
    # Link the hook setter back to the class instance for external access
    control.toggle_state = set_is_on

    # 2. UI Logic (Derived from State)
    # Alignment and Colors are now calculated reactively
    if is_on:
        align = ft.Alignment.CENTER_RIGHT
        thumb_color = ft.Colors.PRIMARY
        thumb_border = ft.Border.all(2, ft.Colors.ON_PRIMARY)
        bg_color = ft.Colors.PRIMARY_CONTAINER
        border_color = ft.Border.all(2, ft.Colors.ON_PRIMARY_CONTAINER)
    else:
        align = ft.Alignment.CENTER_LEFT
        thumb_color = ft.Colors.SECONDARY
        thumb_border = ft.Border.all(2, ft.Colors.ON_SECONDARY)
        bg_color = ft.Colors.SECONDARY_CONTAINER
        border_color = ft.Border.all(2, ft.Colors.ON_SECONDARY_CONTAINER)

    async def _on_click(_: ft.ControlEvent) -> None:
        new_state = not is_on
        set_is_on(new_state) # Triggers reactive re-render
        
        # SFX Logic
        audio_manager.play_sfx(sfx.ui.buttons.switch_on if new_state else sfx.ui.buttons.switch_off)
        
        # Callback logic
        if control.on_toggle:
            result = control.on_toggle(new_state)
            if inspect.isawaitable(result): await result
    
    def _on_hover(e: ft.ControlEvent) -> None:
        if e.data: audio_manager.play_sfx(sfx.ui.buttons.hover_1)
    
    def _on_focus(_: ft.ControlEvent) -> None:
        audio_manager.play_sfx(sfx.ui.buttons.hover_1)
    
    # 3. Component Tree
    # The 'thumb' alignment is now tied to the 'align' variable
    thumb = ft.Container(
        width=control.width / 2, 
        height=control.height,
        bgcolor=thumb_color,
        border=thumb_border,
        align=align, # Reactively updated
        animate_align=ft.Animation(500, ft.AnimationCurve.EASE_IN_OUT_CUBIC_EMPHASIZED),
        animate=ft.Animation(500, ft.AnimationCurve.EASE_IN_OUT),
    )
    
    return ft.Container(
        width=control.width,
        height=control.height,
        bgcolor=bg_color,
        border=border_color,
        animate=ft.Animation(500, ft.AnimationCurve.EASE_IN_OUT),
        content=ft.Button(
            content=thumb,
            on_click=_on_click,
            on_hover=_on_hover,
            on_focus=_on_focus,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=0),
                padding=0,
            ),
            expand=True
        )
    )

# Helper for creation
def NewSwitch(initial_value: bool = False, on_toggle: SwitchEventCallable = None) -> CustomSwitch:
    return CustomSwitchComponent(CustomSwitch(initial_value=initial_value, on_toggle=on_toggle))


# * --- TextAndToggle ---
class TextAndToggle(ft.Container):
    def __init__(
        self,
        label_text: str = "",
        label_size: ft.Number = 30,
        switch_value: bool = False, *,
        label_offset: ft.Offset = ft.Offset(0.0, 0.0),
        # Standard Flet Container properties for positioning
        left: Optional[ft.Number] = None,
        right: Optional[ft.Number] = None,
        top: Optional[ft.Number] = None,
        bottom: Optional[ft.Number] = None,
    ) -> None:
        super().__init__(left=left, right=right, top=top, bottom=bottom)
        self.label_text = label_text
        self.label_size = label_size
        self.label_offset = label_offset
        self.switch_value = switch_value
        # Initialize the stateful class
        self.switch = CustomSwitch(initial_value=switch_value)

@ft.component
def TextAndToggleComponent(control: TextAndToggle, spacer_width: ft.Number = None) -> ft.Control:
    """This component 'unpacks' the class and builds the reactive UI."""
    return ft.Container(
        left=control.left, right=control.right, top=control.top, bottom=control.bottom,
        content=ft.Row(
            controls=[
                ft.Text(
                    control.label_text, size=control.label_size,
                    font_family=FontStyles.ADAPA, color=ft.Colors.WHITE_70,
                    offset=control.label_offset
                ),
                ft.Container(width=(60 if spacer_width is None else None)),
                CustomSwitchComponent(control.switch)
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        )
    )

def NewTextAndToggle(
    label_text: str = "",
    label_size: ft.Number = 30,
    switch_value: bool = False, *,
    spacer_width: ft.Number = None,
    label_offset: ft.Offset = ft.Offset(0.0, 0.0),
    left: Optional[ft.Number] = None,
    right: Optional[ft.Number] = None,
    top: Optional[ft.Number] = None,
    bottom: Optional[ft.Number] = None,
) -> TextAndToggle:
    """Helper that provides full type hinting for your custom arguments."""
    return TextAndToggleComponent(
        TextAndToggle(
            label_text, label_size,
            switch_value,
            label_offset=label_offset,
            left=left, right=right,
            top=top, bottom=bottom
        ), spacer_width=spacer_width
    )