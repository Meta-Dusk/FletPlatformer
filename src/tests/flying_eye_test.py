import flet as ft
import random

from entities.features.entity_data import Factions, AnimConfig
from entities.entity import Entity
from entities.flying_eye import FlyingEye
from audio.audio_manager import global_audio_manager as audio_manager
from images import Sprite
from tests.test_templates import test_init
from tests.dummy_hero import DummyHero
from managers.game_loop import GameLoop

async def test(page: ft.Page) -> None:
    """Test for the `Enemy` class; a simple implementation"""
    await test_init(page)
    
    async def on_death(_) -> None: await flying_eye.death()
    
    def on_change_mv(e: ft.ControlEvent) -> None:
        # Update the flag in our new DummyHero class
        dummy_player.should_move = e.data
        print(f"[DummyPlayer] Set 'should_move' to: {e.data}")
        if not e.data:
            dummy_player.velocity.dx = 0
            dummy_player.states.is_moving = False
            
    def on_change_death(e: ft.ControlEvent) -> None:
        dummy_player.states.dead = e.data
        if e.data:
            toggle_player_mv_loop.value = False
            toggle_player_mv_loop.disabled = True
            toggle_player_mv_loop.update()
            dummy_player.should_move = False
            dummy_player.velocity.dx = 0
            dummy_player.states.is_moving = False
        else:
            toggle_player_mv_loop.disabled = False
            toggle_player_mv_loop.update()
    
    async def on_revive(_) -> None: await flying_eye.revive()
    def on_attack_ranged(_) -> None:
        flying_eye._flip_sprite_x(random.choice([-1, 1]))
        flying_eye.attack_ranged()
    
    attack_btn = ft.Button("Ranged Attack", on_click=on_attack_ranged)
    death_btn = ft.Button("Death", on_click=on_death)
    damage_btn = ft.Button("Take Damage", on_click=lambda _: flying_eye.take_damage(1, is_crit=True))
    revive_btn = ft.Button("Revive", on_click=on_revive)
    
    toggle_player_btn = ft.Switch(adaptive=True, value=False, label="Toggle Player Death", on_change=on_change_death)
    toggle_player_mv_loop = ft.Switch(adaptive=True, value=True, label="Toggle Player Movement", on_change=on_change_mv)
    
    buttons_row = ft.Row(
        controls=[attack_btn, death_btn, damage_btn, revive_btn, toggle_player_btn, toggle_player_mv_loop],
        left=60, top=30
    )
    
    entity_list: list[Entity] = []
    
    game_loop = GameLoop(page, entity_list, audio_manager)
    projectile_manager = game_loop.projectile_manager
    projectile_manager.debug = True
    projectile_layer = projectile_manager.projectile_layer
    
    player_spr = Sprite("images/players/hero_knight/idle_0.png", width=180, height=180, offset=ft.Offset(0, 0.225))
    
    # Use the new DummyHero class
    dummy_player = DummyHero(player_spr, "Dummy Hero", page, audio_manager, Factions.HUMAN, entity_list)
    dummy_player.should_move = True
    dummy_player.states.restrict_movement = True
    
    dummy_player.toggle_show_border(True)
    dummy_player.animations = {
        "idle": AnimConfig(frame_count=11, frame_duration=0.075),
        "run": AnimConfig(frame_count=8, frame_duration=0.075),
    }
    
    flying_eye = FlyingEye(
        page, audio_manager, dummy_player, entity_list=entity_list,
        projectile_manager=projectile_manager,
        enemy_manager=game_loop.enemy_manager
    )
    flying_eye.toggle_show_border(show_border=True, show_atk_hb=True)
    
    entity_list.extend([dummy_player, flying_eye])
    
    game_loop.start()
    
    stage = ft.Stack(
        [dummy_player(), flying_eye(), projectile_layer, buttons_row],
        expand=True
    )
    
    page.add(stage)
    
ft.run(test, assets_dir="../assets")