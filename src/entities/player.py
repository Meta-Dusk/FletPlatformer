from src.utilities import setup_path
setup_path.configure()

import asyncio
import flet as ft
from src.entities.entity import Entity
from src.images import Sprite
from src.audio.audio_manager import AudioManager
from src.audio.sfx_data import SFXList
from pynput import keyboard
from src.utilities.keyboard_manager import held_keys


class Player(Entity):
    """Handles the player's actions and states."""
    def __init__(
        self, page: ft.Page, audio_manager: AudioManager,
        held_keys: set = set()
    ):
        self.audio_manager = audio_manager
        self.held_keys = held_keys
        sprite = Sprite(
            src="images/player/idle_0.png", width=180, height=180,
            offset=ft.Offset(0, 0.275)
        )
        name = "Player"
        super().__init__(sprite=sprite, name=name, page=page)
        self._jump_task: asyncio.Task = None
        self._attack_task: asyncio.Task = None
        self._animation_loop_task: asyncio.Task = None
        self._handler_str = "Player"
    
    def _play_sfx(self, sfx: SFXList):
        right_vol = (self.stack.left + (self.sprite.width / 2)) / self.page.width
        left_vol = 1.0 - right_vol
        self.audio_manager.play_sfx(sfx, left_vol, right_vol)
    
    async def _animation_loop(self):
        """Handles the player's different animation loops."""
        index = 0
        while not self.states.dead:
            # Give way to other animations
            if self.states.is_attacking or self.states.jumped:
                await asyncio.sleep(0.1) # ? Important logic delay
                continue
            
            # Falling animation
            if self.states.is_falling:
                if index > 2: index = 0
                await asyncio.sleep(0.1)
                self.sprite.change_src(f"images/player/fall_{index}.png")
                continue
            
            # Running animation
            if self.states.is_moving:
                if index > 7: index = 0
                wait_time = 0.05 if self.states.sprint else 0.075
                await asyncio.sleep(wait_time)
                self.sprite.change_src(f"images/player/run_{index}.png")
                if index == 2: self._play_sfx(SFXList.ARMOR_RUSTLE_2)
                if index == 5: self._play_sfx(SFXList.ARMOR_RUSTLE_3)
            else: # Idle animation
                if index > 10: index = 0
                await asyncio.sleep(0.075)
                self.sprite.change_src(f"images/player/idle_{index}.png")
            index += 1
    
    async def _jump_anim(self):
        """Handles the player's jump animation."""
        self._play_sfx(SFXList.ROUGH_CLOTH)
        self._play_sfx(SFXList.INHALE_EXHALE_SHORT)
        for i in range(3):
            await asyncio.sleep(0.1)
            if self.states.is_attacking: continue # ? Skips animation if attacking mid-air
            self.sprite.change_src(f"images/player/jump_{i}.png")
        await asyncio.sleep(self.stats.jump_air_time)
        self.states.jumped = False
        self._jump_task = None
    
    async def _attack_anim(self):
        """Handles the player's attack animations with combos."""
        prefix = "attack-main" if self.states.attack_phase == 1 else "attack-secondary"
        for i in range(7):
            await asyncio.sleep(0.1)
            if i == 2 and self.states.attack_phase == 1: # Upward slash
                self._play_sfx(SFXList.FAST_SWORD_WOOSH)
                self._play_sfx(SFXList.SMALL_GRUNT)
            elif i == 1 and self.states.attack_phase == 2: # Downward slash
                self._play_sfx(SFXList.SWORD_TING)
                self._play_sfx(SFXList.GRUNT)
            self.sprite.change_src(f"images/player/{prefix}_{i}.png")
        self.states.is_attacking = False
        self._attack_task = None
    
    async def _movement_loop(self):
        """Handles player movements."""
        while not self.states.dead:
            # is_ctrl_held = keyboard.Key.ctrl_l in keyboard_manager.held_keys # ? Enable if needed
            is_shift_held = keyboard.Key.shift in self.held_keys
            # print(f"keyboard_manager.held_keys: {keyboard_manager.held_keys} | shift:{is_shift_held}, ctrl:{is_ctrl_held}")
            if self.page.window.focused and not self.states.is_attacking:
                step = 20 if is_shift_held else 10
                dx, dy = 0, 0
                # if 'w' in keyboard_manager.held_keys: dy -= step # ? Use for flying upwards
                # if 's' in keyboard_manager.held_keys: dy += step # ? Use for flying downwards
                if 'a' in self.held_keys: dx -= step
                if 'd' in self.held_keys: dx += step
                if dx != 0 or dy != 0: self._debug_msg(f"Moving with: ({dx}, {dy})")
                self.stack.left += dx
                self.stack.bottom -= dy
                
                if ( # ? Manages asset flip direction
                    (dx > 0 and self.sprite.scale.scale_x < 0) or
                    (dx < 0 and self.sprite.scale.scale_x > 0)
                ): 
                    self.sprite.flip_x()
                    self._play_sfx(SFXList.ARMOR_RUSTLE)
                
                # ? Checks for user inputting movement
                if dx > 0 or dx < 0 or dy > 0 or dy < 0:
                    self.states.is_moving = True
                    if is_shift_held: self.states.sprint = True
                    else: self.states.sprint = False
                else: self.states.is_moving = False
            else:
                # Reset state if doing nothing or window not focused
                self.states.is_moving = False
                self.states.sprint = False
                
            if self.stack.bottom < 0:
                # ? Grounding
                self.stack.bottom += 10
                if self.stack.bottom > 0: self.stack.bottom = 0
                    
            elif self.stack.bottom > 0 and not self.states.jumped:
                # ? Gravity
                # if dx == 0 and dy == 0: # ? Turns off gravity during movement
                self.states.is_falling = True
                self.stack.bottom -= 25
                if self.stack.bottom <= 0:
                    self._play_sfx(SFXList.JUMP_LANDING)
                    self._play_sfx(SFXList.EXHALE)
                
            elif self.stack.bottom == 0: self.states.is_falling = False
            if self.stack.page: self.stack.update()
            await asyncio.sleep(0.05) # ? Delay for logic just in case
    
    def _get_jump_dy(self):
        """Returns the total jump distance."""
        _dist = float(self.stats.jump_distance)
        _str = self.stats.jump_strength
        return int(_dist * _str)
    
    def _start_animation_loop(self):
        """Starts the animation loop and stores it in a variable."""
        self._animation_loop_task = self.page.run_task(self._animation_loop)
    
    async def _death_anim(self):
        """Handles the player's death animation."""
        for i in range(11):
            await asyncio.sleep(0.1)
            if i == 3: self._play_sfx(SFXList.DEATH)
            if i == 4: self._play_sfx(SFXList.CLOTHES_DROP)
            if i == 5: self._play_sfx(SFXList.ARMOR_HIT_SOFT)
            if i == 6: 
                self._play_sfx(SFXList.DROP_KEYS)
                self._play_sfx(SFXList.BLADE_DROP)
            self.sprite.change_src(f"images/player/death_{i}.png")
    
    async def death(self):
        """Cancels all running tasks, and plays the death animation."""
        self._debug_msg("Player has died!")
        self.states.dead = True
        if self._movement_loop_task and not self._movement_loop_task.done():
            self._movement_loop_task.cancel()
        if self._animation_loop_task and not self._animation_loop_task.done():
            self._animation_loop_task.cancel()
        if self._jump_task and not self._jump_task.done():
            self._jump_task.cancel()
        if self._attack_task and not self._attack_task.done():
            self._attack_task.cancel()
        await self._death_anim()
    
    def jump(self):
        """Play jump action."""
        if self.stack.bottom == 0 and not self.states.jumped:
            self.stack.bottom += self._get_jump_dy()
            if self.stack.page: self.stack.update()
            self.states.jumped = True
            self._jump_task = asyncio.create_task(
                coro=self._jump_anim(),
                name="[Player] Jumping :: Start animation"
            )
    
    def attack(self):
        """Player attack. Combo cycles: 1 -> 2 -> 1."""
        if self.states.is_attacking: return
        self.states.attack_phase += 1
        if self.states.attack_phase > 2 or self.states.jumped: self.states.attack_phase = 1
        self._debug_msg(f"Attacking! Phase: {self.states.attack_phase}")
        self.states.is_attacking = True
        self._attack_task = asyncio.create_task(
            coro=self._attack_anim(),
            name="[Player] Attacking :: Start animation"
        )
    
    def __call__(self):
        """
        Returns the `Stack` control, and starts the movement and
        animation loops.
        """
        self._start_animation_loop()
        self._start_movement_loop()
        return super().__call__()

# * Test for the Player class
# ? Run with: uv run py -m src.entities.player
from ..utilities.keyboard_manager import start as km_start

def test(page: ft.Page):
    page.title = "Player Class Test"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    audio_manager = AudioManager(debug=True)
    audio_manager.initialize()
    km_start()
    
    async def player_die(_): await player.death()
    
    player = Player(page, audio_manager, held_keys)
    death_btn = ft.Button(
        content="Die", on_click=player_die,
        width=120, height=30,
        left=(page.width / 2) - 60, top=0
    )
    stage = ft.Stack(
        controls=[player(), death_btn],
        expand=True
    )
    
    async def on_keyboard_event(e: ft.KeyboardEvent):
        """Handles 'on-press' events for the player."""
        match e.key:
            case " ": player.jump()
            case "V": player.attack()
            case "Escape": await page.window.close()
    
    page.add(stage)
    page.on_keyboard_event = on_keyboard_event
    
if __name__ == "__main__":
    ft.run(test, assets_dir="../assets")