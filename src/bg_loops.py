import asyncio
import flet as ft
from typing import Callable

from entities.player import Player
from entities.entity import Entity
from entities.enemy import Enemy
from utilities.components import try_update


async def light_mv_loop(background_stack: ft.Stack):
    """
    The movement loop for the light in the `background_stack`.
    Pass this directly in the `page.run_task()` method.\n
    Example: `page.run_task(light_mv_loop)`
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
    background_stack: ft.Stack, foreground_stack: ft.Stack,
    page: ft.Page, player: Player, entity_list: list[Entity],
    stage: ft.Stack,
    post_callback: Callable[[None], None] = None
):
    """
    Handles the stage panning to either left or right.
    Pass this directly in the `page.run_task()` method.\n
    Example: `page.run_task(stage_panning_loop)`\n
    `post_callback()` is called after panning the stage.
    """
    # Constants for configuration
    PAN_STEP = 928 / 2
    EDGE_THRESHOLD = 20
    PAN_ANIM_DURATION = 1000 # ms
    IGNORED_LAYERS = {3, 6}
    LAYER_STEPS = {
        1: 0.2,
        2: 0.4,
        4: 0.6,
        5: 0.8
    }
    
    async def perform_pan(step_amount: float):
        """Helper to move world elements and handle entity states."""
        
        ref_anim_dur: dict[int, int] = {}
        
        # --- HELPER FOR WRAPPING ---
        def move_and_wrap(img: ft.Image, speed_mult: float):
            nonlocal ref_anim_dur
            
            # 1. Move
            img.left += step_amount * speed_mult
            
            # 2. Wrap (The new part)
            # Check if data is dict (new setup) or int (fallback)
            if isinstance(img.data, dict):
                width = img.data["width"]
                
                # Total width of the 3-image chain
                total_span = width * 3
                
                # A buffer to ensure it's fully off-screen before snapping
                # (Using 100px safety margin)
                if img.left + width < -100:
                    img.left += total_span # Snap from Left -> Far Right
                    img.opacity = 0
                    try_update(img)
                    
                elif img.left > page.width + 100:
                    img.left -= total_span # Snap from Right -> Far Left
                    img.opacity = 0
                    try_update(img)

        # Move Backgrounds
        for bg in background_stack.controls:
            bg: ft.Image
            # Handle data being dict (new) or int (old)
            layer_idx = bg.data["layer"] if isinstance(bg.data, dict) else bg.data
            
            if layer_idx in IGNORED_LAYERS: continue
            
            speed = LAYER_STEPS.get(layer_idx, 1)
            move_and_wrap(bg, speed)
                
        # Move Foregrounds
        for fg in foreground_stack.controls:
            move_and_wrap(fg, 1.0)
            
        # Handle Entities
        for entity in entity_list:
            entity.states.disable_movement = True
            entity.states.invincible = True
            entity.stack.left += step_amount
            entity.stack.animate_position.duration = PAN_ANIM_DURATION
        
        try_update(stage)
        await asyncio.sleep(2)
        
        for bg in background_stack.controls:
            bg.opacity = 1
            
        for fg in foreground_stack.controls:
            fg.opacity = 1
        
        # Restore Entity States
        for entity in entity_list:
            entity.states.disable_movement = False
            entity.states.invincible = False
            entity.stack.animate_position.duration = 100
        if post_callback: post_callback()
        try_update(stage)
        
    while True:
        await asyncio.sleep(1)
        # Calculate positions
        player_x = player.stack.left
        player_right_edge = player_x + player.sprite.width
        screen_right_edge = page.width - EDGE_THRESHOLD
        step_to_take = 0
        is_panning: bool = False
        
        if player.states.is_falling or player.states.jumped: continue
        
        # Check Left Edge
        if player_x <= EDGE_THRESHOLD:
            print("[stage_panning_loop] Panning to the left!")
            # If hitting left wall, world moves RIGHT (Positive)
            step_to_take = abs(PAN_STEP)
            is_panning = True
            
        # Check Right Edge
        elif player_right_edge >= screen_right_edge:
            print("[stage_panning_loop] Panning to the right!")
            # If hitting right wall, world moves LEFT (Negative)
            step_to_take = -abs(PAN_STEP)
            is_panning = True
            
        # Execute only if a step was calculated
        if step_to_take != 0: await perform_pan(step_to_take)
        
        # Entity Cleanup
        for entity in entity_list:
            if not is_panning: break
            if entity._cleanup_ready and isinstance(entity, Enemy):
                enemy: Enemy = entity
                print(f"[stage_panning_loop] Cleaning up: {enemy.name}")
                enemy.remove_selves()
        else:
            print(f"[stage_panning_loop] entity_list is now: {len(entity_list)}")
            print(f"[stage_panning_loop] Entities: {entity_list}")
        