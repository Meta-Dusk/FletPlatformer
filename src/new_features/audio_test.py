import flet as ft
import flet_audio as fta

from tests.test_templates import test_init

async def main(page: ft.Page):
    await test_init(page)
    
    test_audio = fta.Audio(
        "audio/sfx/alarm.wav",
        on_loaded=lambda _: print("Loaded audio sample"),
        volume=0.2
    )
    
    @ft.component
    def AudioControls():
        return ft.Column(
            controls=[
                ft.Button("Play", on_click=lambda _: page.run_task(test_audio.play)),
                ft.Button("Pause", on_click=lambda _: page.run_task(test_audio.pause)),
                ft.Button("Resume", on_click=lambda _: page.run_task(test_audio.resume)),
                ft.Button("Release", on_click=lambda _: page.run_task(test_audio.release))
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        
    page.render(AudioControls)

ft.run(main, assets_dir="../assets")