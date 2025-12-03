import flet as ft

from setup import FONT_STYLES

async def test_init(page: ft.Page):
    """The usual page setups for these tests."""
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.fonts = FONT_STYLES
    page.padding = 0
    page.window.title_bar_hidden = True
    
    async def on_keyboard_event(e: ft.KeyboardEvent):
        """Fast exit with key: `[Escape]`."""
        if e.key == "Escape": await page.window.close()
    
    page.on_keyboard_event = on_keyboard_event
    await page.window.center()
