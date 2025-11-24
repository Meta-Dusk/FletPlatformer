import asyncio, random
import flet as ft
from dataclasses import dataclass
from enum import Enum

from entities.entity import Entity
from images import Sprite
from audio.audio_manager import AudioManager
from audio.sfx_data import SFXList


@dataclass
class EnemyData:
    name: str
    width: ft.Number
    height: ft.Number

class EnemyType(Enum):
    """Available enemy types."""
    # TODO: Finish processing the other enemy assets
    # FLYING_EYE = EnemyData("Flying Eye", 150, 150)
    GOBLIN = EnemyData("Gobby", 150, 150)
    # MUSHROOM = EnemyData("Mushy", 150, 150)
    # SKELETON = EnemyData("Skelly", 150, 150)

class Enemy(Entity):
    """Handles an enemy's actions and states."""
    def __init__(
        self, type: EnemyType, page: ft.Page,
        audio_manager: AudioManager
    ):
        self._enemy_name = type.name.lower()
        _sprite = Sprite(
            src=f"images/enemies/{self._enemy_name}/idle_0.png",
            width=type.value.width, height=type.value.height
        )
        _name = type.value.name
        super().__init__(
            sprite=_sprite, name=_name, page=page,
            audio_manager=audio_manager
        )
        # ? No jump sprites available
        self._attack_task: asyncio.Task = None
        self._animation_loop_task: asyncio.Task = None
        self._handler_str = self.name
        self._is_in_range: bool = False
    
    # ? === LOOPING ANIMATIONS ===
    async def _animation_loop(self):
        """Handles an enemy's different animation loops."""
        index: int = 0
        while not self.states.dead:
            # Give way to other animations
            if self.states.is_attacking:
                await asyncio.sleep(0.1) # ? Important logic delay
                continue
            
            # Running animation
            if self.states.is_moving:
                if index > 7: index = 0
                wait_time = 0.075
                await asyncio.sleep(wait_time)
                self.sprite.change_src(self._get_spr_path("run", index))
                # if index == 2: self._play_sfx(SFXList.ARMOR_RUSTLE_2)
                # if index == 5: self._play_sfx(SFXList.ARMOR_RUSTLE_3)
            else: # Idle animation
                if index > 3: index = 0
                await asyncio.sleep(0.1)
                self.sprite.change_src(self._get_spr_path("idle", index))
            index += 1
    
    def _start_animation_loop(self):
        """Starts the animation loop and stores it in a variable."""
        self._animation_loop_task = self.page.run_task(self._animation_loop)
    
    # ? === MOVEMENT LOOP OVERRIDE ===
    async def _movement_loop(self):
        """Handles the enemy's movements."""
        while not self.states.dead:
            if not self.states.is_attacking:
                dx, dy = 0, 0
                rand_m = random.randint(-20, 20)
                if rand_m == 0: continue
                dx += self.stats.movement_speed * rand_m
                self._debug_msg(f"Moving with: ({dx}, {dy})")
                self.stack.left += dx
                self.stack.bottom += dy
                self.stack.animate_position.duration = 100 * abs(rand_m)
                
                if ( # ? Manages asset flip direction
                    (dx > 0 and self.sprite.scale.scale_x < 0) or
                    (dx < 0 and self.sprite.scale.scale_x > 0)
                ): self.sprite.flip_x()
                
                if dx > 0 or dx < 0 or dy > 0 or dy < 0: self.states.is_moving = True
                
                self._update_stack()
                await asyncio.sleep(0.1 * abs(rand_m))
                self.states.is_moving = False
                self._debug_msg("Idling for 2s")
                await asyncio.sleep(2)
            
            else: self.states.is_moving = False
            await asyncio.sleep(0.05)
        
    
    # ? === ONE-SHOT ANIMATIONS ===
    async def _attack_anim(self):
        """Handles the enemy's attack animations with combos."""
        prefix = "attack-main" if self.states.attack_phase == 1 else "attack-secondary"
        for i in range(8):
            await asyncio.sleep(0.1)
            # if i == 2 and self.states.attack_phase == 1:
            #     self._play_sfx(SFXList.FAST_SWORD_WOOSH)
            #     self._play_sfx(SFXList.SMALL_GRUNT)
            # elif i == 1 and self.states.attack_phase == 2:
            #     self._play_sfx(SFXList.SWORD_TING)
            #     self._play_sfx(SFXList.GRUNT)
            self.sprite.change_src(self._get_spr_path(prefix, i))
        self.states.is_attacking = False
        self._attack_task = None
    
    async def _death_anim(self):
        """Handles the enemy's death animation."""
        for i in range(4):
            await asyncio.sleep(0.1)
            # if i == 3: self._play_sfx(SFXList.DEATH)
            # if i == 4: self._play_sfx(SFXList.CLOTHES_DROP)
            # if i == 5: self._play_sfx(SFXList.ARMOR_HIT_SOFT)
            # if i == 6: 
            #     self._play_sfx(SFXList.DROP_KEYS)
            #     self._play_sfx(SFXList.BLADE_DROP)
            self.sprite.change_src(self._get_spr_path("death", i))
        
    # ? === CALLABLE PLAYER ACTIONS/EVENTS ===
    async def death(self):
        """Cancels all running tasks, and plays the death animation."""
        self._debug_msg(f"{self.name} has died!")
        self.states.dead = True
        
    def attack(self):
        """
        Enemy attack. Melee combo cycles: 1 -> 2 -> 1.
        Ranged attack based on distance to player.
        """
        if self.states.is_attacking: return
        self.states.attack_phase += 1
        if self.states.attack_phase > 2: self.states.attack_phase = 1
        self._debug_msg(f"Attacking! Phase: {self.states.attack_phase}")
        self.states.is_attacking = True
        self._attack_task = asyncio.create_task(
            coro=self._attack_anim(),
            name=f"[{self._handler_str}] Attacking :: Start animation"
        )
        
    # ? === OTHER HELPERS ===
    def __call__(self, start_loops: bool = True):
        if start_loops:
            self._start_animation_loop()
            self._start_movement_loop()
        return super().__call__()


# * Test for the Enemy class; a simple implementation
# ? Run with: uv run py -m src.entities.enemy
def test(page: ft.Page):
    page.title = "Enemy Class Test"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 0
    
    audio_manager = AudioManager()
    
    enemy = Enemy(EnemyType.GOBLIN, page, audio_manager)
    stage = ft.Stack(controls=[enemy()], expand=True)
    
    page.add(stage)
    
if __name__ == "__main__":
    ft.run(test, assets_dir="../assets")