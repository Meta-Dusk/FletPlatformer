import flet as ft
import asyncio

from tests.test_templates import test_init
from utilities.splash_handler import SplashHandler
from setup import FontStyles


async def test_splash(page: ft.Page) -> None:
    def on_cleanup() -> None:
        page.controls.clear()
        page.update()
    
    splash_handler = SplashHandler()
    splash_handler.on_cleanup = on_cleanup
    
    text = ft.Text(
        value="Splash 1", size=50, opacity=0, color=ft.Colors.ORANGE,
        animate_opacity=ft.Animation(1000, ft.AnimationCurve.LINEAR),
        font_family=FontStyles.DUNGEON
    )
    page.add(text)
    page.on_keyboard_event = splash_handler.on_skip_event
    
    @splash_handler.skippable_animation()
    async def splash_animation():
        await asyncio.sleep(0.1)
        text.opacity = 1
        text.update()
        await asyncio.sleep(1)
        text.opacity = 0
        text.update()
        await asyncio.sleep(1)
        text.value = "Splash 2"
        text.opacity = 1
        text.update()
        await asyncio.sleep(1)
        text.opacity = 0
        text.update()
        await asyncio.sleep(1)
    
    success = await splash_animation()
    if not success: print("Skipped splash animation.")

async def test(page: ft.Page) -> None:
    await test_init(page)
    await test_splash(page)
    await test_init(page)
    
    page.add(ft.Text("Hello :)", size=40))
    
    
ft.run(test, assets_dir="../assets")