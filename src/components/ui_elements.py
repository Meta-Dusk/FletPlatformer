import flet as ft
import asyncio
from typing import Optional


# * === COMPONENT PRESETS ===
def simple_icon_button(
    icon: ft.IconDataOrControl,
    icon_color: ft.ColorValue = ft.Colors.PRIMARY,
    on_click: Optional[ft.ControlEventHandler[ft.IconButton]] = None
) -> ft.IconButton:
    """Literally just an `IconButton` with a default `icon_color`."""
    return ft.IconButton(
        icon=icon, icon_color=icon_color, on_click=on_click
    )

# * === PRE-ASSEMBLED COMPONENTS ===
# | Buttons |
def fullscreen_button(page: ft.Page) -> ft.IconButton:
    """Handles the window maximizing functionality."""
    def update_icon():
        nonlocal btn
        btn.icon = set_icon()
        try: btn.update()
        except RuntimeError: pass
        
    def set_icon() -> ft.IconData:
        if page.window.maximized: icon = ft.Icons.FULLSCREEN_EXIT
        else: icon = ft.Icons.FULLSCREEN
        return icon
    
    def on_click(_): page.window.maximized = not page.window.maximized
        
    page.on_resize = lambda _: update_icon()
    btn = simple_icon_button(icon=set_icon(), on_click=on_click)
    if not page.window.maximizable: btn.visible = False
    return btn

def minimize_button(page: ft.Page) -> ft.IconButton:
    """Handles the window minimizing functionality."""
    def on_click(_):
        page.window.minimized = True
        page.window.update()
    return simple_icon_button(icon=ft.Icons.MINIMIZE, on_click=on_click)

def exit_button(
    page: ft.Page,
    on_click: Optional[ft.ControlEventHandler[ft.IconButton]] = None
) -> ft.IconButton:
    """
    A simple exit button. If `on_click` is `None`, then it will be set
    to a function that calls the `close()` method from the `page`'s
    `window`.
    """
    if on_click is None:
        on_click = lambda _: asyncio.create_task(
            coro=page.window.close(),
            name="Exit Button -> Closing Window"
        )
    return simple_icon_button(icon=ft.Icons.CLOSE, on_click=on_click)

# | App Bar |
def preset_appbar(title: str, actions: list[ft.Control]) -> ft.AppBar:
    """An `AppBar` that has its `title` component wrapped in a `WindowDragArea`."""
    return ft.AppBar(
        title=ft.WindowDragArea(
            content=ft.Text(value=title, color=ft.Colors.PRIMARY), maximizable=False
        ),
        actions=actions, bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        actions_padding=4, title_spacing=4, leading_width=8, leading=ft.Container(),
        toolbar_height=50, adaptive=True, elevation=8, visible=False
    )