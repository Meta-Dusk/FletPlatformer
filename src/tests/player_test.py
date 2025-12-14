import flet as ft
from pynput import keyboard

import utilities.keyboard_manager as kb_manager
from audio.audio_manager import global_audio_manager
from entities.hero_knight import HeroKnight
from tests.test_templates import test_init
from managers.game_loop import GameLoop

async def test(page: ft.Page):
    """Test for the `Player` class; a simple implementation"""
    await test_init(page)
    kb_manager.start()
    
    def toggle_st_verbose(_):
        if player._stamina_bar_stack is not None:
            player._stamina_bar_stack.verbose = not player._stamina_bar_stack.verbose
    
    def on_toggle_hud(e: ft.ControlEvent) -> None:
        player.show_hud = e.data
    
    player = HeroKnight(page, global_audio_manager, kb_manager.held_keys, debug=True)    
    entity_list = [player]
    
    game_loop = GameLoop(page, entity_list)
    game_loop.start()
    projectile_manager = game_loop.projectile_manager
    projectile_manager.debug = True
    player.projectile_manager = projectile_manager
    
    take_dmg_btn = ft.Button("Take Damage", on_click=lambda _: player.take_damage(5, is_crit=True))
    toggle_borders_btn = ft.Button("Toggle Borders", on_click=lambda _: player.toggle_show_border())
    st_verbose_btn = ft.Button("Toggle Stamina Verbosity", on_click=toggle_st_verbose)
    revive_btn = ft.Button("Revive", on_click=lambda _: player.revive())
    death_btn = ft.Button("KYS", on_click=lambda _: player.death())
    heal_btn = ft.Button("Heal", on_click=lambda _: player.heal(5, overheal=False))
    hide_hud_switch = ft.Switch(label="HUD", value=True, on_change=on_toggle_hud)
    
    ui_col = ft.Column(
        controls=[
            take_dmg_btn, toggle_borders_btn, st_verbose_btn, revive_btn,
            death_btn, heal_btn, hide_hud_switch
        ],
        alignment=ft.MainAxisAlignment.CENTER, top=20, left=20
    )
    
    stage = ft.Stack(
        controls=[player(), projectile_manager.projectile_layer, ui_col],
        expand=True
    )
    
    def on_kb_press(e: kb_manager.KeyType):
        """Handles 'on-press' events for the player."""
        match e:
            case keyboard.Key.space: player.jump()
            case 'v': player.attack()
            case 'b': player.attack_ranged()
            case keyboard.Key.esc: page.run_task(page.window.close)
    
    kb_manager.on_press_callback = on_kb_press
    page.add(stage)
    
ft.run(test, assets_dir="../assets")