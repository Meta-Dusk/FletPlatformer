import asyncio, random
import flet as ft
from pynput import keyboard

from entities.entity import Entity, EntityStates, EntityStats
from images import Sprite
from audio.audio_manager import AudioManager
from audio.sfx_data import SFXLibrary
from utilities.keyboard_manager import held_keys
from utilities.tasks import attempt_cancel

sfx = SFXLibrary()

class Player(Entity):
    """Handles the player's actions and states."""
    def __init__(
        self, page: ft.Page, audio_manager: AudioManager,
        held_keys: set = set(), restrict_traversal: bool = True
    ):
        self.held_keys = held_keys
        self.restrict_traversal = restrict_traversal
        sprite = Sprite(
            src="images/player/idle_0.png", width=180, height=180,
            offset=ft.Offset(0, 0.15)
        )
        name = "Player 1"
        super().__init__(
            sprite=sprite, name=name, page=page,
            audio_manager=audio_manager
        )
        self._jump_task: asyncio.Task = None
        self._attack_task: asyncio.Task = None
        self._take_hit_task: asyncio.Task = None
        self._animation_loop_task: asyncio.Task = None
        self._handler_str = "Player"
        self._revivable: bool = False
        self.health_bar: ft.ProgressBar = None
    
    # ? === LOOPING ANIMATIONS ===
    async def _animation_loop(self):
        """Handles the player's different animation loops."""
        index: int = 0
        while not self.states.dead:
            # Give way to other animations
            if self._interrupt_action():
                await asyncio.sleep(0.1) # ? Important logic delay
                continue
            
            # Falling animation
            if self.states.is_falling:
                if index > 2: index = 0
                await asyncio.sleep(0.1)
                self.sprite.change_src(self._get_spr_path("fall", index))
            
            # Running animation
            if self.states.is_moving and not self.states.is_falling:
                if index > 7: index = 0
                wait_time = 0.05 if self.states.sprint else 0.075
                await asyncio.sleep(wait_time)
                self.sprite.change_src(self._get_spr_path("run", index))
                if index == 2: self._play_sfx(sfx.armor.rustle_2)
                if index == 5: self._play_sfx(sfx.armor.rustle_3)
                
            # Idle animation
            elif not self.states.is_moving and not self.states.is_falling:
                if index > 10: index = 0
                await asyncio.sleep(0.075)
                self.sprite.change_src(self._get_spr_path("idle", index))
                
            index += 1
    
    def _start_animation_loop(self):
        """Starts the animation loop and stores it in a variable."""
        self._animation_loop_task = self.page.run_task(self._animation_loop)
    
    # ? === MOVEMENT LOOP OVERRIDE ===
    async def _movement_loop(self):
        """Handles player movements."""
        while True:
            if not self.states.dead and not self.states.disable_movement:
                # is_ctrl_held = keyboard.Key.ctrl_l in keyboard_manager.held_keys # ? Enable if needed
                is_shift_held = keyboard.Key.shift in self.held_keys
                # print(f"keyboard_manager.held_keys: {keyboard_manager.held_keys} | shift:{is_shift_held}, ctrl:{is_ctrl_held}")
                if (
                    self.page.window.focused and
                    (not self.states.is_attacking and not self.states.taking_damage)
                ):
                    step = self.stats.movement_speed * 2 if is_shift_held else self.stats.movement_speed
                    dx, dy = 0, 0
                    # if 'w' in keyboard_manager.held_keys: dy -= step # ? Use for flying upwards
                    # if 's' in keyboard_manager.held_keys: dy += step # ? Use for flying downwards
                    if 'a' in self.held_keys: dx -= step
                    if 'd' in self.held_keys: dx += step
                    if dx != 0 or dy != 0: self._debug_msg(f"Moving with: ({dx}, {dy})")
                    if (self.stack.left + dx) <= 0 or (self.stack.left + dx + self.sprite.width) >= self.page.width: dx = 0
                    self.stack.left += dx
                    self.stack.bottom -= dy
                    
                    if ( # ? Manages asset flip direction
                        (dx > 0 and self.sprite.scale.scale_x < 0) or
                        (dx < 0 and self.sprite.scale.scale_x > 0)
                    ): 
                        self.sprite.flip_x()
                        self._play_sfx(sfx.armor.rustle_1)
                    
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
                    
            elif self.states.disable_movement: self.states.is_moving = False
            
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
                    self._play_sfx(sfx.player.jump_landing)
                    self._play_sfx(sfx.player.exhale)
                
            elif self.stack.bottom == 0: self.states.is_falling = False
            try: self.stack.update()
            except RuntimeError: pass
            await asyncio.sleep(0.05) # ? Delay for logic just in case
    
    # ? === ONE-SHOT ANIMATIONS ===
    async def _revive_anim(self):
        """Handles the player's revival animation."""
        index = 10
        self._play_sfx(sfx.magic.strike)
        while index >= 0:
            await asyncio.sleep(0.1)
            if index == 5: self._play_sfx(sfx.armor.rustle_3)
            self.sprite.change_src(self._get_spr_path("death", index))
            index -= 1
    
    async def _jump_anim(self):
        """Handles the player's jump animation."""
        self._play_sfx(sfx.cloth.rough_rustle)
        self._play_sfx(sfx.player.inhale_exhale_short)
        for i in range(3):
            await asyncio.sleep(0.1)
            if self.states.is_attacking: continue # ? Skips animation if attacking mid-air
            self.sprite.change_src(self._get_spr_path("jump", i))
        await asyncio.sleep(self.stats.jump_air_time)
        self.states.jumped = False
        self._jump_task = None
    
    async def _attack_anim(self):
        """Handles the player's attack animations with combos."""
        prefix = "attack-main" if self.states.attack_phase == 1 else "attack-secondary"
        for i in range(7):
            await asyncio.sleep(0.1)
            if i == 2 and self.states.attack_phase == 1: # Upward slash
                self._play_sfx(sfx.sword.fast_woosh)
                self._play_sfx(sfx.player.small_grunt)
            elif i == 1 and self.states.attack_phase == 2: # Downward slash
                self._play_sfx(sfx.sword.ting)
                self._play_sfx(sfx.player.grunt)
            self.sprite.change_src(self._get_spr_path(prefix, i))
        self.states.is_attacking = False
        self._attack_task = None
    
    async def _death_anim(self):
        """Handles the player's death animation."""
        death_sfx = [sfx.player.death_1, sfx.player.death_2]
        for i in range(11):
            await asyncio.sleep(0.1)
            if i == 3: self._play_sfx(random.choice(death_sfx))
            if i == 4: self._play_sfx(sfx.cloth.clothes_drop)
            if i == 5: self._play_sfx(sfx.armor.hit_soft)
            if i == 6: 
                self._play_sfx(sfx.item.keys_drop)
                self._play_sfx(sfx.sword.blade_drop)
            self.sprite.change_src(self._get_spr_path("death", i))
        self._revivable = True
    
    async def _take_hit_anim(self):
        """Handles the player's taking damage animation."""
        for i in range(4):
            await asyncio.sleep(0.1)
            if i == 1: self._play_sfx(sfx.player.grunt_hurt)
            self.sprite.change_src(self._get_spr_path("take-hit", i))
        self.states.taking_damage = False
        self._take_hit_task = None
    
    # ? === CALLABLE PLAYER ACTIONS/EVENTS ===
    async def death(self):
        """Cancels all running tasks, and plays the death animation."""
        if self.states.dead:
            self._debug_msg(f"{self.name} is already dead")
            return
        self._debug_msg(f"{self.name} has died!")
        self._revivable = False
        self._reset_states()
        self.states.dead = True
        self.stats.health = 0
        await self._update_health_bar()
        attempt_cancel(self._animation_loop_task)
        self._cancel_temp_tasks()
        await self._death_anim()
    
    def jump(self):
        """Play jump action."""
        if self.stack.bottom != 0 or self._interrupt_action(): return
        self.stack.bottom += self._get_jump_dy()
        try: self.stack.update()
        except RuntimeError: pass
        self.states.jumped = True
        self._jump_task = asyncio.create_task(
            coro=self._jump_anim(),
            name="[Player] Jumping :: Start animation"
        )
    
    def attack(self):
        """Player attack. Combo cycles: 1 -> 2 -> 1."""
        if self.states.is_attacking or self.states.taking_damage or self.states.dead: return
        self.states.attack_phase += 1
        if self.states.attack_phase > 2 or self.states.jumped: self.states.attack_phase = 1
        self._debug_msg(f"Attacking! Phase: {self.states.attack_phase}")
        self.states.is_attacking = True
        self._attack_task = asyncio.create_task(
            coro=self._attack_anim(),
            name=f"[{self._handler_str}] Attacking :: Start animation"
        )
        
    async def take_damage(self, damage_amount: float):
        """Decrease player's health with logic."""
        if self.states.dead:
            self._debug_msg(f"{self.name} is already dead")
            return
        if self.states.taking_damage:
            self._debug_msg(f"{self.name} cannot be damaged again yet")
            return
        self.stats.health -= damage_amount
        self._debug_msg(f"Took damage: {damage_amount}, health is now: {self.stats.health}")
        self.states.taking_damage = True
        if self.stats.health <= 0: await self.death()
        else:
            self._take_hit_task = asyncio.create_task(
                coro=self._take_hit_anim(),
                name=f"[{self._handler_str}] Taking Damage :: Start animation"
            )
        await self._update_health_bar()
    
    async def revive(self):
        if not self.states.dead:
            self._debug_msg(f"{self.name} is not dead")
            return
        elif not self._revivable:
            self._debug_msg(f"{self.name} is not yet ready to be revived")
            return
        self._revivable = False
        self._debug_msg(f"Reviving: {self.name}")
        await self._revive_anim()
        self._reset_states()
        self.stats.health = self.stats.max_health
        attempt_cancel(self._movement_loop_task)
        await self._update_health_bar()
        self._start_loops()
    
    # ? === OTHER HELPERS ===
    def _cancel_temp_tasks(self):
        """Cancels all running temporary tasks."""
        tasks = [
            self._jump_task,
            self._attack_task,
            self._take_hit_task
        ]
        for task in tasks: attempt_cancel(task)
        
    def _start_loops(self):
        self._start_animation_loop()
        self._start_movement_loop()
    
    def __call__(self, start_loops: bool = True):
        """
        Returns the `Stack` control, and starts the movement and
        animation loops.
        """
        if start_loops: self._start_loops()
        return super().__call__()
    
    def _interrupt_action(self):
        """
        Returns `False` if there are no interrupting actions occurring.
        """
        if (
            self.states.is_attacking
            or self.states.jumped
            or self.states.taking_damage
            or self.states.dead
        ): return True
        else:
            self._cancel_temp_tasks()
            return False
    
    def _reset_states(self):
        """Reset palyer state values back to their defaults."""
        self.states = EntityStates()
    
    def _reset_stats(self):
        """Reset player statistics back to their defaults."""
        self.stats = EntityStats()
    
    async def _update_health_bar(self):
        if self.health_bar is None: return
        await asyncio.sleep(0.1)
        self.health_bar.value = abs((self.stats.health / self.stats.max_health) - 1)
        try: self.health_bar.update()
        except RuntimeError: pass
        
    def _get_jump_dy(self):
        """Returns the total jump distance."""
        _dist = float(self.stats.jump_distance)
        _str = self.stats.jump_strength
        return int(_dist * _str)
    

# * Test for the Player class; a simple implementation
# ? Run with: uv run py -m src.entities.player
from utilities.keyboard_manager import start as km_start

def test(page: ft.Page):
    page.title = "Player Class Test"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    audio_manager = AudioManager()
    audio_manager.initialize()
    km_start()
    
    async def player_die(_): await player.take_damage(5)
    
    player = Player(page, audio_manager, held_keys)
    take_dmg_btn = ft.Button(content="Take Damage", on_click=player_die, left=60, top=0)
    stage = ft.Stack(controls=[player(), take_dmg_btn], expand=True)
    
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