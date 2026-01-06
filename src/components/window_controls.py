import flet as ft
from typing import Callable, Optional

from components.custom_switches import NewSwitch
from setup import FontStyles

class FullscreenToggle(ft.Container):
    """Configuration class for the Fullscreen Toggle."""
    def __init__(
        self, *,
        left: Optional[ft.Number] = None,
        right: Optional[ft.Number] = None,
        top: Optional[ft.Number] = None,
        bottom: Optional[ft.Number] = None,
        ref: Optional[ft.Ref[ft.Control]] = None,
    ) -> None:
        super().__init__(left=left, right=right, top=top, bottom=bottom, ref=ref)
        # External hook so SettingsMenu can force a refresh if the window state changes
        self.sync_ui: Callable[[], None] = lambda: None

@ft.component
def FullscreenToggleComponent(control: FullscreenToggle):
    # 1. Reactive State: Does the UI think we are maximized?
    is_maximized, set_is_maximized = ft.use_state(False)

    # 2. Sync Logic: Pull the actual state from the Window property
    def sync():
        if control.page:
            set_is_maximized(control.page.window.maximized)
    
    # Expose the sync method to the class instance for external access
    control.sync_ui = sync

    # 3. Effect: Initial sync when the toggle first appears
    ft.use_effect(sync, [])

    # 4. Action: Toggle the actual window state
    def handle_toggle(val: bool):
        # In 0.81.0, property changes on page are handled via binary protocol
        control.page.window.maximized = val
        set_is_maximized(val)

    # 5. UI Construction
    label = ft.Text(
        "Borderless Fullscreen", 
        size=30,
        font_family=FontStyles.ADAPA, 
        color=ft.Colors.WHITE_70
    )

    return ft.Container(
        alignment=ft.Alignment.CENTER,
        padding=4,
        expand=True,
        content=ft.Row(
            controls=[
                ft.Container(content=label, offset=ft.Offset(-0.1, 0.0)),
                ft.Container(width=30), # Spacer
                NewSwitch(
                    initial_value=is_maximized,
                    on_toggle=handle_toggle
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
    )

def NewFullscreenToggle(
    *,
    left: Optional[ft.Number] = None,
    right: Optional[ft.Number] = None,
    top: Optional[ft.Number] = None,
    bottom: Optional[ft.Number] = None,
    ref: Optional[ft.Ref[ft.Control]] = None,
) -> FullscreenToggle:
    """Helper with full type hinting to create a reactive FullscreenToggle."""
    return FullscreenToggleComponent(
        FullscreenToggle(left=left, right=right, top=top, bottom=bottom, ref=ref)
    )