import flet as ft

from utilities.keyboard_manager import start as km_start, held_keys
from audio.audio_manager import global_audio_manager
from entities.player import Player
from tests.test_templates import test_init


async def test(page: ft.Page):
    """Test for the `Player` class; a simple implementation"""
    await test_init(page)
    
    km_start()
    
    async def player_dmg(_): await player.take_damage(5)
    
    player = Player(page, global_audio_manager, held_keys, debug=True)
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
    
    page.on_keyboard_event = on_keyboard_event
    page.add(stage)
    
ft.run(test, assets_dir="../assets")