import asyncio
import flet as ft
from entities.player import Player


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
    player: Player,
    page: ft.Page
):
    # Constants for configuration
    PAN_STEP = 928 / 2
    EDGE_THRESHOLD = 20
    PAN_ANIM_DURATION = 1000 # ms
    IGNORED_LAYERS = {3, 6}  # Using a set for faster lookups
    
    async def perform_pan(step_amount: float):
        """Helper to move world elements and handle player state."""
        # Move Backgrounds
        for bg in background_stack.controls:
            if bg.data not in IGNORED_LAYERS:
                bg.left += step_amount
                bg.update()
                
        # Move Foregrounds
        for fg in foreground_stack.controls:
            fg.left += step_amount
            fg.update()
            
        # Move Player & Handle Animation
        player.states.disable_movement = True
        
        # Save previous animation speed, set to slow pan speed
        prev_dur = player.stack.animate_position.duration
        player.stack.animate_position.duration = PAN_ANIM_DURATION
        
        player.stack.left += step_amount
        player.stack.update()
        await asyncio.sleep(2)
        
        # Restore Player State
        player.states.disable_movement = False
        player.stack.animate_position.duration = prev_dur
        player.stack.update()
        
    while True:
        await asyncio.sleep(1)
        # Calculate calculated positions
        player_x = player.stack.left
        player_right_edge = player_x + player.sprite.width
        screen_right_edge = page.width - EDGE_THRESHOLD
        step_to_take = 0
        
        if player.states.is_falling or player.states.jumped: continue
        
        # Check Left Edge
        if player_x <= EDGE_THRESHOLD:
            print("Panning to the left!")
            # If hitting left wall, world moves RIGHT (Positive)
            step_to_take = abs(PAN_STEP)
            
        # Check Right Edge
        elif player_right_edge >= screen_right_edge:
            print("Panning to the right!")
            # If hitting right wall, world moves LEFT (Negative)
            step_to_take = -abs(PAN_STEP)
            
        # Execute only if a step was calculated
        if step_to_take != 0: await perform_pan(step_to_take)