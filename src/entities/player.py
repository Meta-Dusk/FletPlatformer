import asyncio, random
import flet as ft
from pynput import keyboard

from entities.entity import Entity, EntityStates, EntityStats, Factions
from images import Sprite
from audio.audio_manager import AudioManager
from audio.sfx_data import SFXLibrary
from utilities.keyboard_manager import held_keys
from utilities.tasks import attempt_cancel
from utilities.collisions import check_collision

sfx = SFXLibrary()

class Player(Entity):
    """Handles the player's actions and states."""
    def __init__(
        self, page: ft.Page, audio_manager: AudioManager,
        held_keys: set = set(), *, debug: bool = False,
        restrict_traversal: bool = True
    ):
        self.held_keys = held_keys
        self.restrict_traversal = restrict_traversal
        sprite = Sprite(
            src="images/player/idle_0.png", width=180, height=180,
            offset=ft.Offset(0, 0.15)
        )
        self.name = "Hero Knight"
        self._handler_str = "Player"
        super().__init__(
            sprite=sprite, name=self.name, page=page,
            audio_manager=audio_manager, faction=Factions.HUMAN,
            debug=debug
        )
        self._jump_task: asyncio.Task = None
        self._attack_task: asyncio.Task = None
        self._take_hit_task: asyncio.Task = None
        self._animation_loop_task: asyncio.Task = None
        self._entity_list: list[Entity] = None
    
    # * === LOOPING ANIMATIONS ===
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
    
    # * === CUSTOM MOVEMENT LOOP ===
    async def _movement_loop(self):
        """Handles player movements."""
        while True:
            for entity in self._entity_list:
                if entity.faction != Factions.HUMAN and entity.states.dealing_damage:
                    if check_collision(
                        self.stack.left, self.stack.bottom, self.sprite.width, self.sprite.height,
                        entity.stack.left, entity.stack.bottom, entity.sprite.width, entity.sprite.height
                    ): await self.take_damage(entity.stats.attack_damage)
            if not self.states.dead and not self.states.disable_movement:
                is_shift_held = keyboard.Key.shift in self.held_keys
                # is_ctrl_held = keyboard.Key.ctrl_l in keyboard_manager.held_keys # ? Enable if needed
                # print(f"keyboard_manager.held_keys: {keyboard_manager.held_keys} | shift:{is_shift_held}, ctrl:{is_ctrl_held}")
                if (
                    self.page.window.focused and
                    (not self.states.is_attacking and not self.states.taking_damage)
                ):
                    current_scale_x = self.sprite.scale.scale_x if hasattr(self.sprite.scale, "scale_x") else self.sprite.scale
                    start_facing_sign = 1 if current_scale_x > 0 else -1
                    
                    step = self.stats.movement_speed * 2 if is_shift_held else self.stats.movement_speed
                    dx, dy = 0, 0
                    
                    # if 'w' in keyboard_manager.held_keys: dy -= step # ? Use for flying upwards
                    # if 's' in keyboard_manager.held_keys: dy += step # ? Use for flying downwards
                    if 'a' in self.held_keys: dx -= step
                    if 'd' in self.held_keys: dx += step
                    if (self.stack.left + dx) <= 0 or (self.stack.left + dx + self.sprite.width) >= self.page.width: dx = 0
                    
                    # ? Movement
                    if dx != 0 or dy != 0:
                        self.states.is_moving = True
                        if is_shift_held: self.states.sprint = True
                        else: self.states.sprint = False
                        
                        self._debug_msg(f"Moving with: ({dx}, {dy})")
                        self.stack.left += dx
                        self.stack.bottom -= dy
                        
                        # ? Sprite flipping logic
                        desired_sign = start_facing_sign
                        if dx > 0: desired_sign = 1
                        elif dx < 0: desired_sign = -1
                        
                        has_flipped = False
                        if desired_sign != start_facing_sign:
                            new_scale = abs(current_scale_x) * desired_sign
                            self.sprite.scale = ft.Scale(scale_x=new_scale, scale_y=self.sprite.scale.scale_y)
                            has_flipped = True
                        
                        if has_flipped: 
                            self.sprite.try_update()
                            self._play_sfx(sfx.armor.rustle_1)
                    else: self.states.is_moving = False
                    
                else:
                    # ? Reset state if doing nothing or window not focused
                    self.states.is_moving = False
                    self.states.sprint = False
                    
            else: self.states.is_moving = False
            
            # ? Grounding
            if self.stack.bottom < 0:
                self.stack.bottom += 10
                if self.stack.bottom > 0: self.stack.bottom = 0
                
            # ? Gravity
            elif self.stack.bottom > 0 and not self.states.jumped:
                self.states.is_falling = True
                self.stack.bottom -= 25
                if self.stack.bottom <= 0:
                    self._play_sfx(sfx.player.jump_landing)
                    self._play_sfx(sfx.player.exhale)
                
            elif self.stack.bottom == 0: self.states.is_falling = False
            if self.states.is_moving or self.states.is_falling: self._safe_update(self.stack)
            await asyncio.sleep(0.05) # ? Delay for logic just in case
    
    # * === ONE-SHOT ANIMATIONS ===
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
            if i == 3 or i == 4: self.states.dealing_damage = True
            else: self.states.dealing_damage = False
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
        self.states.revivable = True
    
    async def _take_hit_anim(self):
        """Handles the player's taking damage animation."""
        for i in range(4):
            await asyncio.sleep(0.1)
            if i == 1: self._play_sfx(sfx.player.grunt_hurt)
            self.sprite.change_src(self._get_spr_path("take-hit", i))
        self.states.taking_damage = False
        self._take_hit_task = None
    
    # * === CALLABLE PLAYER ACTIONS/EVENTS ===
    async def death(self):
        """Cancels all running tasks, and plays the death animation."""
        if not super().death(): return
        self._debug_msg(f"{self.name} has died!")
        self._reset_states(EntityStates(dead=True))
        self._reset_stats(EntityStats(health=0))
        await self._update_health_bar()
        
        attempt_cancel(self._animation_loop_task)
        self._cancel_temp_tasks()
        await self._death_anim()
    
    def jump(self):
        """Play jump action."""
        if self.stack.bottom != 0 or self._interrupt_action(): return
        self.stack.bottom += self._get_jump_dy()
        self._safe_update(self.stack)
        self.states.jumped = True
        self._jump_task = self.page.run_task(self._jump_anim)
    
    def attack(self):
        """Player attack. Combo cycles: 1 -> 2 -> 1."""
        if not super().attack(): return
        self.states.attack_phase += 1
        if self.states.attack_phase > 2 or self.states.jumped: self.states.attack_phase = 1
        self._debug_msg(f"Attacking! Phase: {self.states.attack_phase}")
        self.states.is_attacking = True
        self._attack_task = self.page.run_task(self._attack_anim)
        
    async def take_damage(self, damage_amount: float):
        """Decrease player's health with logic."""
        if not super().take_damage(): return
        self.stats.health -= damage_amount
        self._debug_msg(f"Took damage: {damage_amount}, health is now: {self.stats.health}")
        self.states.taking_damage = True
        if (self.states.is_attacking and self.states.jumped) or self.states.is_attacking:
            attempt_cancel(self._attack_task)
            self.states.is_attacking = False
            self._safe_update(self.stack)
        if self.stats.health <= 0: await self.death()
        else: self._take_hit_task = self.page.run_task(self._take_hit_anim)
        await self._update_health_bar()
    
    async def revive(self):
        if not super().revive(): return
        self.states.revivable = False
        self._debug_msg(f"Reviving: {self.name}")
        await self._revive_anim()
        self._reset_states()
        self._reset_stats()
        attempt_cancel(self._movement_loop_task)
        await self._update_health_bar()
        self._start_loops()
    
    def __call__(self, start_loops: bool = True):
        """
        Returns the `Stack` control, and starts the movement and
        animation loops.
        """
        if start_loops: self._start_loops()
        return super().__call__()
    
    # * === OTHER HELPERS ===
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
    
    audio_manager = AudioManager(debug=False)
    audio_manager.initialize()
    km_start()
    
    async def player_dmg(_): await player.take_damage(5)
    
    player = Player(page, audio_manager, held_keys, debug=True)
    take_dmg_btn = ft.Button(content="Take Damage", on_click=player_dmg, left=60, top=0)
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