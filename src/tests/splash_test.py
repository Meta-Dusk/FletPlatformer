import flet as ft
import asyncio

from tests.test_templates import test_init
from utilities.splash_handler import SplashHandler
# from setup import FontStyles


async def test_splash(page: ft.Page) -> None:
    def on_cleanup() -> None:
        page.controls.clear()
        page.update()
    
    splash_handler = SplashHandler()
    splash_handler.on_cleanup = on_cleanup
    
    splash_img = ft.Image(
        src="images/splash/brand.png", width=355, height=265,
        fit=ft.BoxFit.COVER, gapless_playback=True,
        filter_quality=ft.FilterQuality.HIGH,
        animate_opacity=ft.Animation(1000, ft.AnimationCurve.LINEAR),
        opacity=0
    )
    page.add(splash_img)
    page.on_keyboard_event = splash_handler.on_skip_event
    
    @splash_handler.skippable_animation()
    async def splash_animation():
        await asyncio.sleep(0.1)
        splash_img.opacity = 1
        splash_img.update()
        await asyncio.sleep(2)
        splash_img.opacity = 0
        splash_img.update()
        await asyncio.sleep(1)
        splash_img.src = "icon.png"
        splash_img.width = 1024 / 2
        splash_img.height = 1024 / 2
        splash_img.opacity = 1
        splash_img.update()
        await asyncio.sleep(2)
        splash_img.opacity = 0
        splash_img.update()
        await asyncio.sleep(1)
    
    success = await splash_animation()
    if not success: print("Skipped splash animation.")

async def test(page: ft.Page) -> None:
    await test_init(page)
    await test_splash(page)
    await test_init(page)
    
    page.add(ft.Text("That was a splash animation :)", size=40))
    
    
ft.run(test, assets_dir="../assets")