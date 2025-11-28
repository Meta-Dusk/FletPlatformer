import flet as ft

from entities.enemy import Enemy, EnemyType, Factions
from entities.entity import Entity
from audio.audio_manager import AudioManager
from utilities.tasks import attempt_cancel
from images import Sprite


def before_test(page: ft.Page):
    page.title = "Enemy Class Test"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 0

def test(page: ft.Page):
    """Test for the `Enemy` class; a simple implementation"""
    audio_manager = AudioManager()
    audio_manager.initialize()
    
    async def on_death(_): await enemy.death()
    async def on_damage(_): await enemy.take_damage(5)
    def on_change_mv(e: ft.ControlEvent):
        if e.data:
            dummy_player._start_movement_loop()
            dummy_player._safe_update(dummy_player.stack)
        else:
            attempt_cancel(dummy_player._movement_loop_task)
            dummy_player.stack.animate_position.duration = 100
            dummy_player._safe_update(dummy_player.stack)
    def on_change_death(e: ft.ControlEvent):
        dummy_player.states.dead = e.data
        if e.data:
            toggle_player_mv_loop.value = False
            toggle_player_mv_loop.disabled = True
            toggle_player_mv_loop.update()
            dummy_player.stack.animate_position.duration = 100
            dummy_player._safe_update(dummy_player.stack)
        else:
            toggle_player_mv_loop.disabled = False
            toggle_player_mv_loop.update()
    
    attack_btn = ft.Button("Attack", on_click=lambda _: enemy.attack())
    death_btn = ft.Button("Death", on_click=on_death)
    damage_btn = ft.Button("Take Damage", on_click=on_damage)
    toggle_player_btn = ft.Switch(adaptive=True, value=False, label="Toggle Player Death", on_change=on_change_death)
    toggle_player_mv_loop = ft.Switch(adaptive=True, value=True, label="Toggle Player Movement", on_change=on_change_mv)
    buttons_row = ft.Row(
        controls=[attack_btn, death_btn, damage_btn, toggle_player_btn, toggle_player_mv_loop],
        left=60, top=30
    )
    
    player_spr = Sprite("images/player/idle_0.png", width=180, height=180, offset=ft.Offset(0, 0.225))
    dummy_player = Entity(player_spr, "Dummy Hero", page, audio_manager, Factions.HUMAN)
    dummy_player.toggle_show_border(True)
    enemy = Enemy(EnemyType.GOBLIN, page, audio_manager, dummy_player, debug=True)
    enemy.toggle_show_border(True)
    enemy._atk_hb_show = True
    
    stage = ft.Stack(controls=[dummy_player(), enemy(), buttons_row], expand=True)
    
    async def on_keyboard_event(e: ft.KeyboardEvent):
        """Fast exit with key: `[Escape]`."""
        if e.key == "Escape": await page.window.close()
    
    page.on_keyboard_event = on_keyboard_event
    page.add(stage)
    dummy_player._start_movement_loop()
    
if __name__ == "__main__":
    ft.run(main=test, before_main=before_test, assets_dir="../assets")