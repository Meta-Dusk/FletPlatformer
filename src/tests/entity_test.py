import flet as ft

from entities.entity import Entity
from entities.enemy import Factions
from images import Sprite
from audio.audio_manager import AudioManager


def before_test(page: ft.Page):
    page.title = "Entity Class Test"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 0

def test(page: ft.Page):
    """Test for the `Entity` class; a simple implementation"""
    audio_manager = AudioManager(debug=False)
    audio_manager.initialize()
    
    entity_spr = Sprite("images/enemies/goblin/idle_0.png", width=150, height=150)
    entity_spr.color = ft.Colors.with_opacity(0.2, ft.Colors.RED)
    entity_spr.color_blend_mode = ft.BlendMode.SRC_A_TOP
    entity = Entity(entity_spr, "Dummy Gob", page, audio_manager, Factions.NONHUMAN, debug=True)
    entity.toggle_show_border(True)
    
    stage = ft.Stack(controls=[entity()], expand=True)
    
    async def on_keyboard_event(e: ft.KeyboardEvent):
        """Fast exit with key: `[Escape]`."""
        if e.key == "Escape": await page.window.close()
    
    page.on_keyboard_event = on_keyboard_event
    page.add(stage)
    entity._start_movement_loop()
    
if __name__ == "__main__":
    ft.run(main=test, before_main=before_test, assets_dir="../assets")