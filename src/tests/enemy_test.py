import flet as ft

from entities.features.entity_data import Factions, AnimConfig
from entities.entity import Entity
from entities.goblin import Goblin
from audio.audio_manager import global_audio_manager
from utilities.tasks import attempt_cancel
from utilities.components import try_update
from images import Sprite
from tests.test_templates import test_init
from managers.game_loop import GameLoop

async def test(page: ft.Page) -> None:
    """Test for the `Enemy` class; a simple implementation"""
    await test_init(page)
    
    async def on_death(_) -> None: await goblin.death()
    
    def on_change_mv(e: ft.ControlEvent) -> None:
        if e.data:
            dummy_player._start_movement_loop()
            try_update(dummy_player.stack)
        else:
            attempt_cancel(dummy_player._movement_loop_task)
            dummy_player.velocity.dx = 0
            dummy_player.states.is_moving = False
            
    def on_change_death(e: ft.ControlEvent) -> None:
        dummy_player.states.dead = e.data
        if e.data:
            toggle_player_mv_loop.value = False
            toggle_player_mv_loop.disabled = True
            toggle_player_mv_loop.update()
            dummy_player.velocity.dx = 0
            dummy_player.states.is_moving = False
        else:
            toggle_player_mv_loop.disabled = False
            toggle_player_mv_loop.update()
    
    async def on_revive(_) -> None: await goblin.revive()
    
    attack_btn = ft.Button("Attack", on_click=lambda _: goblin.attack())
    death_btn = ft.Button("Death", on_click=on_death)
    damage_btn = ft.Button("Take Damage", on_click=lambda _: goblin.take_damage(1, is_crit=True))
    revive_btn = ft.Button("Revive", on_click=on_revive)
    toggle_player_btn = ft.Switch(adaptive=True, value=False, label="Toggle Player Death", on_change=on_change_death)
    toggle_player_mv_loop = ft.Switch(adaptive=True, value=True, label="Toggle Player Movement", on_change=on_change_mv)
    buttons_row = ft.Row(
        controls=[attack_btn, death_btn, damage_btn, revive_btn, toggle_player_btn, toggle_player_mv_loop],
        left=60, top=30
    )
    
    entity_list: list[Entity] = []
    
    player_spr = Sprite("images/players/hero_knight/idle_0.png", width=180, height=180, offset=ft.Offset(0, 0.225))
    dummy_player = Entity(player_spr, "Dummy Hero", page, global_audio_manager, Factions.HUMAN, entity_list)
    dummy_player.toggle_show_border(True)
    dummy_player.states.restrict_movement = True
    dummy_player.animations = {
        "idle": AnimConfig(frame_count=11, frame_duration=0.075),
        "run": AnimConfig(frame_count=8, frame_duration=0.075),
    }
    
    goblin = Goblin(page, global_audio_manager, dummy_player, entity_list=entity_list)
    goblin.toggle_show_border(show_border=True, show_atk_hb=True)
    
    entity_list.extend([dummy_player, goblin])
    
    game_loop = GameLoop(page, entity_list)
    game_loop.start()
    
    stage = ft.Stack(controls=[dummy_player(), goblin(), buttons_row], expand=True)
    
    page.add(stage)
    dummy_player._start_movement_loop()
    
ft.run(test, assets_dir="../assets")