import flet as ft

from utilities.keyboard_manager import start as km_start, held_keys
from audio.audio_manager import global_audio_manager
from entities.hero_knight import HeroKnight
from tests.test_templates import test_init


async def test(page: ft.Page):
    """Test for the `Player` class; a simple implementation"""
    await test_init(page)
    km_start()
    
    async def player_dmg(_): await player.take_damage(5, is_crit=True)
    def toggle_st_verbose(_):
        if player._stamina_bar_stack is not None:
            player._stamina_bar_stack.verbose = not player._stamina_bar_stack.verbose
    
    player = HeroKnight(page, global_audio_manager, held_keys, debug=True)
    
    take_dmg_btn = ft.Button(content="Take Damage", on_click=player_dmg)
    toggle_borders_btn = ft.Button(content="Toggle Borders", on_click=lambda _: player.toggle_show_border())
    st_verbose_btn = ft.Button(content="Toggle Stamina Verbosity", on_click=toggle_st_verbose)
    
    ui_col = ft.Column(
        controls=[take_dmg_btn, toggle_borders_btn, st_verbose_btn],
        alignment=ft.MainAxisAlignment.CENTER, top=20, left=20
    )
    
    stage = ft.Stack(
        controls=[player(), ui_col],
        expand=True
    )
    
    async def on_keyboard_event(e: ft.KeyboardEvent):
        """Handles 'on-press' events for the player."""
        match e.key:
            case " ": player.jump()
            case "V": player.attack()
            case "Escape": await page.window.close()
    
    page.on_keyboard_event = on_keyboard_event
    page.add(stage)
    
ft.run(test, assets_dir="../assets")