import flet as ft

from entities.features.entity_data import Factions, AnimConfig
from entities.entity import Entity
from entities.goblin import Goblin
from audio.audio_manager import global_audio_manager
from utilities.components import try_update
from images import Sprite
from tests.test_templates import test_init
from managers.game_loop import GameLoop

class DummyHero(Entity):
    """A minimal Entity subclass for testing that supports tick_logic."""
    def __init__(self, sprite, name, page, audio, faction, entity_list):
        super().__init__(sprite, name, page, audio, faction, entity_list)
        self.should_move = False
        self.move_speed = 3.0 # Meters per second

    def tick_logic(self, dt: float) -> None:
        """Handle movement if enabled."""
        if self.states.dead:
            self.velocity.dx = 0
            return
            
        if self.should_move:
            # Simple patrol: bounce left/right or just move right
            # For this test, let's just stand still or move based on external toggle?
            # The test toggle just says "Toggle Player Movement".
            # Let's make him walk back and forth.
            if self.velocity.dx == 0: self.velocity.dx = self.move_speed
            
            # Bounce bounds (approximate for test stage)
            if self.stack.left > 800: self.velocity.dx = -self.move_speed
            elif self.stack.left < 100: self.velocity.dx = self.move_speed
            
            self.states.is_moving = True
            self._flip_sprite_x(self.velocity.dx)
        else:
            self.velocity.dx = 0
            self.states.is_moving = False

async def test(page: ft.Page) -> None:
    """Test for the `Enemy` class; a simple implementation"""
    await test_init(page)
    
    async def on_death(_) -> None: await goblin.death()
    
    def on_change_mv(e: ft.ControlEvent) -> None:
        # Update the flag in our new DummyHero class
        dummy_player.should_move = e.data
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
    
    # Use the new DummyHero class
    dummy_player = DummyHero(player_spr, "Dummy Hero", page, global_audio_manager, Factions.HUMAN, entity_list)
    dummy_player.should_move = True # Start moving by default to match switch
    
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
    
ft.run(test, assets_dir="../assets")