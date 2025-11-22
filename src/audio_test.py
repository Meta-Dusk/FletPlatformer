import flet as ft
import pygame


def before_main(page: ft.Page):
    page.title = "Audio Test"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

async def main(page: ft.Page):
    pygame.mixer.init()
    pygame.mixer.music.load("src/assets/audio/music/summer-samba_world-music-bossa-brasil.mp3")
    pygame.mixer.music.play()
    pygame.mixer.music.set_volume(0.5)
    
    page.add(
        ft.Button("Pause Music", on_click=lambda _: pygame.mixer.music.pause()),
        ft.Button("Unpause Music", on_click=lambda _: pygame.mixer.music.unpause()),
        ft.Button("Stop Music", on_click=lambda _: pygame.mixer.music.stop())
    )
    
    await page.window.center()
    

if __name__ == "__main__":
    ft.run(main=main, before_main=before_main)