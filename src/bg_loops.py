import asyncio
import flet as ft

from entities.player import Player
from entities.entity import Entity
from entities.enemy import Enemy
from typing import Callable


async def light_mv_loop(background_stack: ft.Stack):
    """
    The movement loop for the light in the `background_stack`.
    Pass this directly in the `page.run_task()` method.\n
    Example: `page.run_task(light_mv_loop)`
    """
    duration: float = 0.0
    step = 928
    await asyncio.sleep(1)
    while True:
        for bg in background_stack.controls:
            bg: ft.Image
            if bg.data == 3 or bg.data == 6:
                duration = bg.animate_position.duration
                bg.left += step
                bg.update()
        await asyncio.sleep(duration / 1000)
        step *= -1
        
async def stage_panning_loop(
    background_stack: ft.Stack,
    foreground_stack: ft.Stack,
    page: ft.Page,
    player: Player,
    entity_list: list[Entity],
    stage: ft.Stack,
    optional_callable: Callable[[None], None] = None
):
    """
    Handles the stage panning to either left or right.
    Pass this directly in the `page.run_task()` method.\n
    Example: `page.run_task(stage_panning_loop)`
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
        # Move Backgrounds
        for bg in background_stack.controls:
            bg: ft.Image
            if bg.data in IGNORED_LAYERS: continue
            bg.left += step_amount * LAYER_STEPS.get(bg.data, 1)
                
        # Move Foregrounds
        for fg in foreground_stack.controls: fg.left += step_amount
            
        # Handle Entities
        for entity in entity_list:
            entity.states.disable_movement = True
            entity.stack.left += step_amount
            entity.stack.animate_position.duration = PAN_ANIM_DURATION
        
        stage.update()
        await asyncio.sleep(2)
        
        # Restore Entity States
        for entity in entity_list:
            entity.states.disable_movement = False
            entity.stack.animate_position.duration = 100
        if optional_callable is not None: optional_callable()
        stage.update()
        
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
            print("Panning to the left!")
            # If hitting left wall, world moves RIGHT (Positive)
            step_to_take = abs(PAN_STEP)
            is_panning = True
            
        # Check Right Edge
        elif player_right_edge >= screen_right_edge:
            print("Panning to the right!")
            # If hitting right wall, world moves LEFT (Negative)
            step_to_take = -abs(PAN_STEP)
            is_panning = True
        
        # Entity Cleanup
        if is_panning:
            for entity in entity_list:
                if entity._cleanup_ready and isinstance(entity, Enemy):
                    enemy: Enemy = entity
                    enemy.remove_selves()
            
        # Execute only if a step was calculated
        if step_to_take != 0: await perform_pan(step_to_take)