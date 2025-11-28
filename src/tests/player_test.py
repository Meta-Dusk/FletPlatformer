import flet as ft

from utilities.keyboard_manager import start as km_start, held_keys
from audio.audio_manager import AudioManager
from entities.player import Player


def before_test(page: ft.Page):
    page.title = "Player Class Test"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 0

def test(page: ft.Page):
    """Test for the `Player` class; a simple implementation"""
    audio_manager = AudioManager(debug=False)
    audio_manager.initialize()
    km_start()
    
    async def player_dmg(_): await player.take_damage(5)
    
    player = Player(page, audio_manager, held_keys, debug=True)
    player._atk_hb_show = True
    player.toggle_show_border(True)
    take_dmg_btn = ft.Button(content="Take Damage", on_click=player_dmg, left=60, top=20)
    stage = ft.Stack(controls=[player(), take_dmg_btn], expand=True)
    
    async def on_keyboard_event(e: ft.KeyboardEvent):
        """Handles 'on-press' events for the player."""
        match e.key:
            case " ": player.jump()
            case "V": player.attack()
            case "Escape": await page.window.close()
    
    page.add(stage)
    page.on_keyboard_event = on_keyboard_event
    
if __name__ == "__main__":
    ft.run(main=test, before_main=before_test, assets_dir="../assets")