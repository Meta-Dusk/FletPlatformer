import flet as ft

from entities.entity import Entity
from entities.features.entity_data import Factions
from images import Sprite
from audio.audio_manager import global_audio_manager
from tests.test_templates import test_init


async def test(page: ft.Page):
    """Test for the `Entity` class; a simple implementation"""
    await test_init(page)
    
    audio_manager = global_audio_manager
    audio_manager.initialize()
    
    entity_spr = Sprite("images/enemies/goblin/idle_0.png", width=150, height=150)
    entity_spr.color = ft.Colors.with_opacity(0.2, ft.Colors.RED)
    entity_spr.color_blend_mode = ft.BlendMode.SRC_A_TOP
    entity = Entity(entity_spr, "Dummy Gob", page, audio_manager, Factions.NONHUMAN, debug=True)
    entity.toggle_show_border(True)
    
    stage = ft.Stack(controls=[entity()], expand=True)
    
    page.add(stage)
    entity._start_movement_loop()
    
ft.run(test, assets_dir="../assets")