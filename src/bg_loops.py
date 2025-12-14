import asyncio
import flet as ft
from typing import Callable

from entities.features.entity_data import Factions
from entities.enemy import Enemy
from utilities.components import try_update
from managers.game_mixins import GameManagerMimic

async def light_mv_loop(background_stack: ft.Stack):
    """
    The movement loop for the light in the `background_stack`.
    """
    duration: float = 0.0
    step: int = 928
    LIGHT_LAYERS = {3, 6}
    await asyncio.sleep(0.1)
    while True:
        for bg in background_stack.controls:
            if (
                isinstance(bg, ft.Image)
                and isinstance(bg.data, dict)
                and (bg.data["layer"] in LIGHT_LAYERS)
            ):
                duration = bg.animate_position.duration
                bg.left += step
                try_update(bg)
        await asyncio.sleep(duration / 1000)
        step *= -1
        
async def stage_panning_loop(
    game_manager: GameManagerMimic,
    projectile_stack: ft.Stack,
    post_callback: Callable[[None], None] = None,
):
    """
    Handles the stage panning with temporary animation injection for entities.
    """
    # Constants for configuration
    PAN_STEP = 928 / 2
    EDGE_THRESHOLD = 20
    PAN_ANIM_DURATION = 1000 # ms
    IGNORED_LAYERS = {3, 6}
    LAYER_STEPS = {1: 0.2, 2: 0.4, 4: 0.6, 5: 0.8}
    
    async def perform_pan(step_amount: float):
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
                elif img.left > game_manager.page.width + 100:
                    img.left -= total_span
                    img.opacity = 0
                    try_update(img)

        # Move Backgrounds
        for bg in game_manager.background_stack.controls:
            if not isinstance(bg, ft.Image): continue
            layer_idx = bg.data["layer"] if isinstance(bg.data, dict) else bg.data
            
            if layer_idx in IGNORED_LAYERS: continue
            
            speed = LAYER_STEPS.get(layer_idx, 1)
            move_and_wrap(bg, speed)
                
        # Move Foregrounds
        for fg in game_manager.foreground_stack.controls:
            move_and_wrap(fg, 1.0)
            
        # --- HANDLE ENTITIES ---
        for entity in game_manager.entity_list:
            # Lock State (Stops Physics Manager from calculating velocity)
            entity.states.disable_movement = True
            entity.states.invincible = True
            entity.states.is_moving = False
            
            # INJECT Animation Property
            # We add this temporarily so Flet interpolates the position change smoothly
            entity.stack.animate_position = ft.Animation(PAN_ANIM_DURATION, ft.AnimationCurve.EASE_IN_OUT)
        
        all_stacks = [e.stack for e in game_manager.entity_list]
        if all_stacks: try_update(*all_stacks)
        
        await asyncio.sleep(0.05)
        
        for entity in game_manager.entity_list:
            entity.stack.left += step_amount
        
        if all_stacks: try_update(*all_stacks)
                
        # Update stage generally (for BGs)
        try_update(game_manager.stage)
        
        # Wait for Pan to Finish
        await asyncio.sleep(2)
        
        # Restore Opacity for wrapped BG images
        for bg in game_manager.background_stack.controls: bg.opacity = 1
        for fg in game_manager.foreground_stack.controls: fg.opacity = 1
        
        # --- RESTORE ENTITIES (The Cleanup) ---
        for entity in game_manager.entity_list:
            entity.states.disable_movement = False
            entity.states.invincible = False
            
            # 5. REMOVE Animation Property
            # This returns control to the PhysicsManager for the next frame
            entity.stack.animate_position = None
        
        if all_stacks: try_update(*all_stacks)
        
        if post_callback: post_callback()
        try_update(game_manager.stage)
    
    def check_alive_enemies() -> bool:
        return any(e.faction == Factions.NONHUMAN and not e.states.dead for e in game_manager.entity_list)
    
    while True:
        await asyncio.sleep(1)
        if (
            not game_manager.player.stack
            or len(projectile_stack.controls) > 0
            or check_alive_enemies()
        ):
            continue
        
        # Calculate positions
        player_x = game_manager.player.stack.left
        player_right_edge = player_x + game_manager.player.sprite.width
        screen_right_edge = game_manager.page.width - EDGE_THRESHOLD
        step_to_take = 0
        is_panning: bool = False
        
        if game_manager.player.states.is_falling or game_manager.player.states.jumped: continue
        
        # Check Left Edge
        if player_x <= EDGE_THRESHOLD:
            print("[stage_panning_loop] Panning to the left!")
            step_to_take = abs(PAN_STEP)
            is_panning = True
            
        # Check Right Edge
        elif player_right_edge >= screen_right_edge:
            print("[stage_panning_loop] Panning to the right!")
            step_to_take = -abs(PAN_STEP)
            is_panning = True
            
        # Execute
        if step_to_take != 0: await perform_pan(step_to_take)
        
        # Entity Cleanup
        # We iterate a copy of the list slice to safely modify if needed, 
        # though remove_selves handles the list removal safely.
        for entity in game_manager.entity_list[:]: 
            if not is_panning: break
            if entity._cleanup_ready and isinstance(entity, Enemy):
                print(f"[stage_panning_loop] Cleaning up: {entity.name}")
                entity.remove_selves()