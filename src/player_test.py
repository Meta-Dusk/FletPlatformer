import asyncio
import flet as ft
from pynput import keyboard
import utilities.keyboard_manager as keyboard_manager
from audio.music_data import MusicList
from audio.sfx_data import SFXList
from audio.audio_manager import AudioManager


def before_test(page: ft.Page):
    page.title = "Keyboard Detection Test"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 0
    
async def test(page: ft.Page):
    # TODO: Make classes for the player and the enemies
    # * Player Variables
    is_moving: bool = False
    sprint: bool = False
    jumped: bool = False
    jump_task: asyncio.Task = None
    attack_phase: int = 0
    attack_task: asyncio.Task = None
    is_attacking: bool = False
    is_falling: bool = False
    
    # * Setup Keyboard Manager
    keyboard_manager.start()
    
    # * Setup Audio
    audio_manager = AudioManager()
    audio_manager.initialize()
    audio_manager.play_music(MusicList.DREAMS)
    
    # * Setup Widgets
    char_spr = ft.Image(
        src="images/player/idle_0.png", width=180, height=180,
        filter_quality=ft.FilterQuality.NONE, fit=ft.BoxFit.COVER,
        scale=ft.Scale(scale_x=2, scale_y=2), offset=ft.Offset(0, 0.225),
        gapless_playback=True
    )
    nametag = ft.Text(
        value="You", width=100, height=50, size=20, text_align=ft.TextAlign.CENTER,
        offset=ft.Offset(0, 1.5)
    )
    char_column = ft.Column(
        controls=[nametag, char_spr], alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )
    char_stack = ft.Stack(
        controls=[char_column],
        left=(page.width / 2) - (char_spr.width / 2), bottom=0,
        animate_position=ft.Animation(100, ft.AnimationCurve.EASE_IN_OUT)
    )
    stage = ft.Stack(controls=[char_stack], expand=True)
    page.add(stage)
    await page.window.center()
    
    async def animation_loop():
        """Handles the player's different animation loops."""
        index = 0
        while True:
            # Give way to other animations
            if is_attacking or jumped:
                await asyncio.sleep(0.1) # ? Important logic delay
                continue
            
            if is_falling: # Falling animation
                if index > 2: index = 0
                await asyncio.sleep(0.1)
                char_spr.src = f"images/player/fall_{index}.png"
                continue
            
            if is_moving: # Running animation
                if index > 7: index = 0
                wait_time = 0.05 if sprint else 0.075
                await asyncio.sleep(wait_time)
                char_spr.src = f"images/player/run_{index}.png"
                if index == 2: audio_manager.play_sfx(SFXList.ARMOR_RUSTLE_2)
                if index == 5: audio_manager.play_sfx(SFXList.ARMOR_RUSTLE_3)
            else: # Idle animation
                if index > 10: index = 0
                await asyncio.sleep(0.075)
                char_spr.src = f"images/player/idle_{index}.png"
            
            char_spr.update()
            index += 1
    
    async def jump_anim():
        """Player jump animation."""
        nonlocal jump_task, jumped
        audio_manager.play_sfx(SFXList.ROUGH_CLOTH)
        audio_manager.play_sfx(SFXList.INHALE_EXHALE_SHORT)
        for i in range(3):
            await asyncio.sleep(0.1)
            char_spr.src = f"images/player/jump_{i}.png"
            char_spr.update()
        jumped = False
        jump_task = None
    
    async def attack_anim():
        """Player attack animation with combos."""
        nonlocal is_attacking, attack_task
        prefix = "attack-main" if attack_phase == 1 else "attack-secondary"
        for i in range(7):
            await asyncio.sleep(0.1)
            if i == 2 and attack_phase == 1:
                audio_manager.play_sfx(SFXList.FAST_SWORD_WOOSH)
                audio_manager.play_sfx(SFXList.SMALL_GRUNT)
            elif i == 1 and attack_phase == 2:
                audio_manager.play_sfx(SFXList.SWORD_TING)
                audio_manager.play_sfx(SFXList.GRUNT)
            char_spr.src = f"images/player/{prefix}_{i}.png"
            char_spr.update()
        is_attacking = False
        attack_task = None
    
    async def on_keyboard_event(e: ft.KeyboardEvent):
        """Handles 'on-press' events for the player."""
        nonlocal jumped, jump_task
        nonlocal attack_phase, attack_task, is_attacking
        match e.key:
            case " ":
                if char_stack.bottom == 0:
                    char_stack.bottom += 150
                    char_stack.update()
                    jumped = True
                    jump_task = asyncio.create_task(jump_anim())
            case "Escape":
                await page.window.close()
            case "V":
                if is_attacking: # Prevent interrupting an existing attack
                    return
                
                # Cycle phases (Simple 1 -> 2 -> 1 logic)
                attack_phase += 1
                if attack_phase > 2: 
                    attack_phase = 1
                print(f"Attacking! Phase: {attack_phase}")
                is_attacking = True
                attack_task = asyncio.create_task(attack_anim())
                
    async def movement_loop():
        """Handles player movements."""
        nonlocal is_moving, sprint, is_falling
        while True:
            # is_ctrl_held = keyboard.Key.ctrl_l in keyboard_manager.held_keys # ? Enable if needed
            is_shift_held = keyboard.Key.shift in keyboard_manager.held_keys
            # print(f"keyboard_manager.held_keys: {keyboard_manager.held_keys} | shift:{is_shift_held}, ctrl:{is_ctrl_held}")
            if page.window.focused and not is_attacking:
                step = 20 if is_shift_held else 10
                dx, dy = 0, 0
                # if 'w' in keyboard_manager.held_keys: dy -= step # ? Use for flying upwards
                # if 's' in keyboard_manager.held_keys: dy += step # ? Use for flying downwards
                if 'a' in keyboard_manager.held_keys: dx -= step
                if 'd' in keyboard_manager.held_keys: dx += step
                if dx != 0 or dy != 0: print(f"Moving: ({dx}, {dy})")
                char_stack.left += dx
                char_stack.bottom -= dy
                
                if ( # ? Manages asset flip direction
                    (dx > 0 and char_spr.scale.scale_x < 0) or
                    (dx < 0 and char_spr.scale.scale_x > 0)
                ): 
                    char_spr.scale.scale_x *= -1
                    audio_manager.play_sfx(SFXList.ARMOR_RUSTLE)
                
                # ? Checks for user inputting movement
                if dx > 0 or dx < 0 or dy > 0 or dy < 0:
                    is_moving = True
                    if is_shift_held: sprint = True
                    else: sprint = False
                else: is_moving = False
            else:
                # Reset state if doing nothing or window not focused
                is_moving = False
                sprint = False
                
            if char_stack.bottom < 0:
                # ? Grounding
                char_stack.bottom += 10
                if char_stack.bottom > 0: char_stack.bottom = 0
                    
            elif char_stack.bottom > 0 and not jumped:
                # ? Gravity
                # if dx == 0 and dy == 0: # ? Turns off gravity during movement
                is_falling = True
                char_stack.bottom -= 25
                if char_stack.bottom <= 0:
                    audio_manager.play_sfx(SFXList.JUMP_LANDING)
                    audio_manager.play_sfx(SFXList.EXHALE)
                
            elif char_stack.bottom == 0: is_falling = False
            char_stack.update()
            await asyncio.sleep(0.05) # ? Delay for logic just in case
            
    page.on_keyboard_event = on_keyboard_event
    page.run_task(movement_loop)
    page.run_task(animation_loop)
    
    
if __name__ == "__main__":
    ft.run(main=test, before_main=before_test)