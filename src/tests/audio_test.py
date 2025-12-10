import flet as ft
import pygame

from tests.test_templates import test_init

async def main(page: ft.Page):
    await test_init(page)
    
    pygame.mixer.init()
    pygame.mixer.music.load("src/assets/audio/music/Sketchbook 2024-03-20_02.ogg")
    pygame.mixer.music.play()
    pygame.mixer.music.set_volume(0.5)
    
    page.add(
        ft.Button("Pause Music", on_click=lambda _: pygame.mixer.music.pause()),
        ft.Button("Unpause Music", on_click=lambda _: pygame.mixer.music.unpause()),
        ft.Button("Stop Music", on_click=lambda _: pygame.mixer.music.stop())
    )
        
ft.run(main, assets_dir="../assets")