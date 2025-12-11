import flet as ft

from utilities.commands.ui import DevConsole
from tests.test_templates import test_init

async def main(page: ft.Page):
    await test_init(page)
    page.bgcolor = ft.Colors.WHITE
    
    console = DevConsole()
    
    page.overlay.append(console)
    
    async def on_kb(e: ft.KeyboardEvent):
        if e.key == "/":
            await console.toggle()
        elif e.key == "Escape" and console.visible:
            await console.toggle()
        await console.handle_keyboard(e)
        
    page.on_keyboard_event = on_kb
    page.add(ft.Text("Press '/' to open developer console", color=ft.Colors.BLACK))
    await page.window.center()

ft.run(main, assets_dir="../assets")