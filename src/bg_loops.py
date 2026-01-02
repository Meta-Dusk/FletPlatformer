import asyncio
import flet as ft
from typing import Callable

from entities.features.entity_data import Factions
from entities.enemy import Enemy
from utilities.components import try_update
from managers.game_mixins import GameManagerMimic

class LightMovementLoop:
    """
    Handles the simple looping movement of the
    light in the background.
    """
    def __init__(self, background_stack: ft.Stack) -> None:
        self.bg_stack = background_stack
        self.duration: float = 0.0
        self.step: int = 928
        self.light_layers: set[int] = {3, 6}
        self.is_running: bool = False
    
    def stop(self) -> None:
        self.is_running = False
    
    async def start(self) -> None:
        self.is_running = True
        while self.is_running:
            for bg in self.bg_stack.controls:
                if (
                    isinstance(bg, ft.Image)
                    and isinstance(bg.data, dict)
                    and (bg.data["layer"] in self.light_layers)
                ):
                    duration = bg.animate_position.duration
                    bg.left += self.step
                    try_update(bg)
            await asyncio.sleep(duration / 1000)
            self.step *= -1

class StagePanningLoop:
    """
    Handles the loop for panning the game stage whenever
    the player reaches the borders of the screen.
    """
    def __init__(
        self,
        game_manager: GameManagerMimic,
        projectile_stack: ft.Stack,
        post_callback: Callable[[None], None] = None,
    ):
        self.game_manager = game_manager
        self.projectile_stack = projectile_stack
        self.post_callback = post_callback
        
        # Config
        self.pan_step: float = 928 / 2
        self.edge_threshold: int = 20
        self.pan_anim_duration: int = 1000 # ms
        self.ignored_layers: set[int] = {3, 6}
        self.layer_steps: dict[int, float] = {1: 0.2, 2: 0.4, 4: 0.6, 5: 0.8}
        self.is_running: bool = False
        self.check_interval: float = 0.5 # seconds
    
    async def _perform_pan(self, step_amount: float):
        """Helper to move world elements and handle entity states."""
        
        # --- HELPER FOR WRAPPING ---
        def move_and_wrap(img: ft.Image, speed_mult: float):
            # 1. Move
            img.left += step_amount * speed_mult
            
            # 2. Wrap
            if isinstance(img.data, dict):
                width = img.data["width"]
                total_span = width * 3
                
                # Snap Logic
                if img.left + width < -100:
                    img.left += total_span
                    img.opacity = 0
                    try_update(img)
                elif img.left > self.game_manager.page.width + 100:
                    img.left -= total_span
                    img.opacity = 0
                    try_update(img)

        # Move Backgrounds
        for bg in self.game_manager.background_stack.controls:
            if not isinstance(bg, ft.Image): continue
            layer_idx = bg.data["layer"] if isinstance(bg.data, dict) else bg.data
            
            if layer_idx in self.ignored_layers: continue
            
            speed = self.layer_steps.get(layer_idx, 1)
            move_and_wrap(bg, speed)
                
        # Move Foregrounds
        for fg in self.game_manager.foreground_stack.controls:
            move_and_wrap(fg, 1.0)
            
        # --- HANDLE ENTITIES ---
        for entity in self.game_manager.entity_list:
            # Lock State (Stops Physics Manager from calculating velocity)
            entity.states.disable_movement = True
            entity.states.invincible = True
            entity.states.is_moving = False
            entity.stack.animate_position = ft.Animation(self.pan_anim_duration, ft.AnimationCurve.EASE_IN_OUT)
            try_update(entity.stack)
        
        all_stacks = [e.stack for e in self.game_manager.entity_list]
        
        await asyncio.sleep(0.05)
        
        for entity in self.game_manager.entity_list:
            entity.stack.left += step_amount
        
        if all_stacks: try_update(*all_stacks)
                
        # Update stage generally (for BGs)
        try_update(self.game_manager.stage)
        
        # Wait for Pan to Finish
        await asyncio.sleep(2)
        
        # Restore Opacity for wrapped BG images
        for bg in self.game_manager.background_stack.controls: bg.opacity = 1
        for fg in self.game_manager.foreground_stack.controls: fg.opacity = 1
        
        # --- RESTORE ENTITIES (The Cleanup) ---
        for entity in self.game_manager.entity_list:
            entity.states.disable_movement = False
            entity.states.invincible = False
            entity.stack.animate_position = None
        
        if all_stacks: try_update(*all_stacks)
        
        if self.post_callback: self.post_callback()
        try_update(self.game_manager.stage)
    
    def _check_alive_enemies(self) -> bool:
        """Returns `true` if there are any alive enemies in the `entity_list`."""
        return any(e.faction == Factions.NONHUMAN and not e.states.dead for e in self.game_manager.entity_list)
    
    def stop(self) -> None:
        self.is_running = False
    
    async def start(self) -> None:
        self.is_running = True
        
        while self.is_running:
            await asyncio.sleep(self.check_interval)
            if (
                not self.game_manager.player.stack
                or len(self.projectile_stack.controls) > 0
                or self._check_alive_enemies()
            ):
                continue
            
            # Calculate positions
            player_x = self.game_manager.player.stack.left
            player_right_edge = player_x + self.game_manager.player.sprite.width
            screen_right_edge = self.game_manager.page.width - self.edge_threshold
            step_to_take = 0
            is_panning: bool = False
            
            if self.game_manager.player.states.is_falling or self.game_manager.player.states.jumped: continue
            
            # Check Left Edge
            if player_x <= self.edge_threshold:
                print("[stage_panning_loop] Panning to the left!")
                step_to_take = abs(self.pan_step)
                is_panning = True
                
            # Check Right Edge
            elif player_right_edge >= screen_right_edge:
                print("[stage_panning_loop] Panning to the right!")
                step_to_take = -abs(self.pan_step)
                is_panning = True
                
            # Execute
            if step_to_take != 0: await self._perform_pan(step_to_take)
            
            # Entity Cleanup
            # We iterate a copy of the list slice to safely modify if needed, 
            # though remove_selves handles the list removal safely.
            for entity in self.game_manager.entity_list[:]: 
                if not is_panning: break
                if entity._cleanup_ready and isinstance(entity, Enemy):
                    print(f"[stage_panning_loop] Cleaning up: {entity.name}")
                    entity.remove_selves()
