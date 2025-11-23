import flet as ft
from audio.audio_manager import AudioManager
from utilities.keyboard_manager import held_keys, start as km_start
from entities.player import Player


async def main_ui(page: ft.Page):
    page.title = "Player Class Test"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    audio_manager = AudioManager(debug=True)
    audio_manager.initialize()
    km_start()
    
    async def player_die(_): await player.death()
    
    player = Player(page, audio_manager, held_keys)
    death_btn = ft.Button(
        content="Die", on_click=player_die,
        width=120, height=30,
        left=(page.width / 2) - 60, top=0
    )
    stage = ft.Stack(
        controls=[player(), death_btn],
        expand=True
    )
    
    async def on_keyboard_event(e: ft.KeyboardEvent):
        """Handles 'on-press' events for the player."""
        match e.key:
            case " ": player.jump()
            case "V": player.attack()
            case "Escape": await page.window.close()
    
    await page.window.center()
    
    page.add(stage)
    page.on_keyboard_event = on_keyboard_event