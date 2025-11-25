import asyncio
import flet as ft
from audio.audio_manager import AudioManager
from utilities.keyboard_manager import held_keys, start as km_start
from entities.player import Player

# TODO: Add a background

async def main_ui(page: ft.Page):
    light_mv_task: asyncio.Task = None
    stage_panning_task: asyncio.Task = None
    audio_manager = AudioManager(debug=False)
    audio_manager.initialize()
    km_start()
    
    async def light_mv_loop():
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
    
    light_mv_task = page.run_task(light_mv_loop)
    
    async def stage_panning_loop():
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
    
    stage_panning_task = page.run_task(stage_panning_loop)
    
    async def player_die(_): await player.death()
    async def player_damage(_): await player.take_damage(5)
    def da_btn_on_change(e: ft.ControlEvent): audio_manager.directional_sfx = e.data
    async def player_revive(_): await player.revive()
    
    player = Player(page, audio_manager, held_keys)
    death_btn = ft.Button(content="KYS", on_click=player_die, icon=ft.Icons.PERSON_OFF)
    damage_btn = ft.Button(content="Take Damage", on_click=player_damage, icon=ft.Icons.PERSONAL_INJURY)
    revive_btn = ft.Button(content="Revive", on_click=player_revive, icon=ft.Icons.PERSON_OUTLINE)
    directional_audio_btn = ft.Switch(
        adaptive=True, label="Directional Audio",
        value=audio_manager.directional_sfx, on_change=da_btn_on_change
    )
    buttons_row = ft.Row(
        controls=[
            ft.Container(content=revive_btn, padding=16),
            ft.Container(content=death_btn, padding=16),
            ft.Container(content=damage_btn, padding=16),
            ft.Container(content=directional_audio_btn, padding=16),
        ], alignment=ft.MainAxisAlignment.CENTER, top=0, left=40
    )
    nametag = ft.Text(
        value="You", size=20, width=50,
        left=(player.sprite.width / 2) - 25,
        bottom=player.sprite.height - 30,
        text_align=ft.TextAlign.CENTER
    )
    health_bar = ft.ProgressBar(
        value=0, left=(player.sprite.width / 2) - 50,
        bottom=player.sprite.height - 50, width=100,
        bar_height=5, scale=ft.Scale(scale_x=-1, scale_y=1),
        color=ft.Colors.BLACK, bgcolor=ft.Colors.RED, border_radius=5
    )
    player.health_bar = health_bar
    player.stack.controls.extend([nametag, health_bar])
    
    def bg_image_forest(index: int):
        animate_position: ft.Animation = ft.Animation(1000, ft.AnimationCurve.EASE_IN_OUT)
        match index:
            case 0: animate_position = None
            case 1: animate_position = ft.Animation(2000, ft.AnimationCurve.EASE_IN_OUT)
            case 2: animate_position = ft.Animation(1800, ft.AnimationCurve.EASE_IN_OUT)
            case 3 | 6: animate_position = ft.Animation(150000, ft.AnimationCurve.EASE_IN_OUT)
            case 4: animate_position = ft.Animation(1600, ft.AnimationCurve.EASE_IN_OUT)
            case 5: animate_position = ft.Animation(1400, ft.AnimationCurve.EASE_IN_OUT)
            case 7: animate_position = ft.Animation(1200, ft.AnimationCurve.EASE_IN_OUT)
        return ft.Image(
            src=f"images/backgrounds/night_forest/{index}.png", data=index,
            width=928*4 if index == 3 | 6 else 928*2, height=793*2, bottom=0, scale=2,
            filter_quality=ft.FilterQuality.NONE, gapless_playback=True,
            repeat=ft.ImageRepeat.REPEAT if index == 0 else ft.ImageRepeat.REPEAT_X,
            offset=ft.Offset(0, 0.05), left=page.width / 2, animate_position=animate_position,
        )
    
    background_stack = ft.Stack(controls=[], expand=True)
    foreground_stack = ft.Stack(controls=[], expand=True)
    for i in range(7): background_stack.controls.append(bg_image_forest(i))
    background_stack.controls.append(bg_image_forest(9))
    foreground_stack.controls.extend([bg_image_forest(8), bg_image_forest(10)])
    
    stage = ft.Stack(
        controls=[
            background_stack,
            player(),
            foreground_stack,
            buttons_row
        ],
        expand=True
    )
    
    async def on_keyboard_event(e: ft.KeyboardEvent):
        """Handles 'on-press' events for the player."""
        match e.key:
            case " ": player.jump()
            case "V": player.attack()
            case "Escape": await page.window.close()
    
    await page.window.center()
    
    page.add(stage)
    page.on_keyboard_event = on_keyboard_event
    